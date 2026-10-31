import os
from uuid import UUID

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
import requests

from . import mpesa
from .imagesearch import embed, similar
from .models import ChatMessage, Order, Product, StockAlert
from .serializers import ProductSerializer
from .tasks import branded, send_html


class UserOrIpRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AssistantRateThrottle(UserOrIpRateThrottle):
    scope = "assistant"


class AlertRateThrottle(UserOrIpRateThrottle):
    scope = "alerts"


class AccountRegisterRateThrottle(UserOrIpRateThrottle):
    scope = "account_register"


class AccountLoginRateThrottle(UserOrIpRateThrottle):
    scope = "account_login"


def serialize_products(queryset, request):
    return ProductSerializer(queryset, many=True, context={"request": request}).data


@api_view(["GET"])
@permission_classes([AllowAny])
def products(request):
    query = request.GET.get("q", "").strip()[:120]
    category = request.GET.get("category", "").strip()[:40]
    cache_key = f"products:v3:{query.casefold()}:{category.casefold()}"
    data = cache.get(cache_key)
    if data is None:
        queryset = Product.objects.all().order_by("id")
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(subtitle__icontains=query) | Q(category__icontains=query))
        if category:
            queryset = queryset.filter(category__iexact=category)
        data = serialize_products(queryset[:48], request)
        cache.set(cache_key, data, 60)
    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser])
def image_search(request):
    image = request.FILES.get("image")
    if not image or image.size > 5_000_000:
        return Response({"error": "Choose an image under 5 MB."}, status=400)
    try:
        vector = embed(image)
    except (Image.DecompressionBombError, OSError, ValueError, TypeError):
        return Response({"error": "We couldn't read that image. Try a JPG, PNG, or WebP."}, status=400)
    matches = similar(vector, Product.objects.exclude(embedding=None).order_by("id"))
    return Response(serialize_products(matches, request))


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AlertRateThrottle])
def subscribe_alert(request):
    email = str(request.data.get("email", "")).strip()[:254]
    query = str(request.data.get("query", "")).strip()[:200]
    if not query:
        return Response({"error": "Enter a product name to create a stock alert."}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return Response({"error": "Enter a valid email address."}, status=400)
    product = Product.objects.filter(name__icontains=query).first()
    alert, created = StockAlert.objects.get_or_create(email=email, query=query, product=product, notified=False)
    if created:
        send_html.delay(
            email,
            "You're on the list",
            branded("We'll let you know", f"We'll email you as soon as “{query}” is available.", "Keep browsing", settings.FRONTEND_URL),
        )
    return Response({"ok": True}, status=201 if created else 200)


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return Response({"error": "Google sign-in is not configured."}, status=503)
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError
    from google.oauth2 import id_token

    try:
        info = id_token.verify_oauth2_token(
            request.data.get("credential", ""),
            google_requests.Request(),
            client_id,
        )
    except (GoogleAuthError, ValueError, KeyError):
        return Response({"error": "Google sign-in could not verify your account."}, status=401)
    if not info.get("email_verified") or not info.get("email"):
        return Response({"error": "Use a Google account with a verified email address."}, status=401)
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(
        username=info["email"],
        defaults={"email": info["email"], "first_name": info.get("given_name", "")[:150]},
    )
    if not user.email:
        user.email = info["email"]
        user.save(update_fields=["email"])
    return Response({
        "token": Token.objects.get_or_create(user=user)[0].key,
        "name": user.first_name or info["email"],
        "email": user.email,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AccountRegisterRateThrottle])
def account_register(request):
    email = str(request.data.get("email", "")).strip().lower()
    name = str(request.data.get("name", "")).strip()
    password = str(request.data.get("password", ""))
    if not name or len(name) > 150:
        return Response({"error": "Enter your name (up to 150 characters)."}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return Response({"error": "Enter a valid email address."}, status=400)
    if len(email) > 150:
        return Response({"error": "Use an email address with 150 characters or fewer."}, status=400)
    user_model = get_user_model()
    if user_model.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
        return Response({"error": "An account with this email already exists. Sign in instead."}, status=409)
    user = user_model(username=email, email=email, first_name=name)
    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return Response({"error": " ".join(error.messages)}, status=400)
    user.set_password(password)
    try:
        with transaction.atomic():
            user.save()
            token, _ = Token.objects.get_or_create(user=user)
    except IntegrityError:
        return Response({"error": "An account with this email already exists. Sign in instead."}, status=409)
    return Response({"token": token.key, "name": user.first_name, "email": user.email}, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AccountLoginRateThrottle])
def account_login(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = str(request.data.get("password", ""))
    if not email or not password:
        return Response({"error": "Enter your email and password."}, status=400)
    user_model = get_user_model()
    account = user_model.objects.filter(email__iexact=email).first()
    user = authenticate(request, username=account.username if account else email, password=password)
    if not user:
        return Response({"error": "Email or password is incorrect."}, status=401)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "name": user.first_name or email, "email": user.email})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    request.auth.delete()
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def checkout_quote(request):
    product = get_object_or_404(Product, pk=request.query_params.get("product"), stock__gt=0)
    if product.price_min <= 0:
        return Response({"error": "This laptop does not have a valid checkout price yet."}, status=400)
    try:
        quantity = int(request.query_params.get("qty", "1"))
    except (TypeError, ValueError):
        return Response({"error": "Choose a valid quantity."}, status=400)
    if not 1 <= quantity <= product.stock:
        return Response({"error": "That quantity is not available."}, status=400)
    amount = mpesa.kes_amount(product.price_min * quantity)
    if amount is None:
        return Response({"error": "This laptop does not have a valid checkout price yet."}, status=400)
    return Response({"amount_kes": amount, "quantity": quantity})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    try:
        product_id = request.data["product"]
        quantity = int(request.data.get("qty", 1))
    except (KeyError, TypeError, ValueError):
        return Response({"error": "Choose a valid product and quantity."}, status=400)
    if quantity < 1:
        return Response({"error": "Quantity must be at least one."}, status=400)
    try:
        phone = mpesa.normalize(request.data.get("phone", ""))
    except ValueError as error:
        return Response({"error": str(error)}, status=400)

    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
        if product.stock < quantity:
            return Response({"error": "The requested quantity is no longer available."}, status=400)
        if product.price_min <= 0:
            return Response({"error": "This laptop does not have a valid checkout price yet."}, status=400)
        amount_kes = mpesa.kes_amount(product.price_min * quantity)
        if amount_kes is None:
            return Response({"error": "This laptop does not have a valid checkout price yet."}, status=400)
        order = Order.objects.create(
            user=request.user,
            product=product,
            qty=quantity,
            amount=product.price_min * quantity,
            payment_amount=amount_kes,
            phone=phone,
        )

    try:
        result = mpesa.stk_push(phone, amount_kes, f"TUVA{order.pk}")
    except (KeyError, ValueError):
        order.status = "failed"
        order.save(update_fields=["status"])
        return Response({"error": "M-PESA credentials are incomplete or the phone number is invalid."}, status=503)
    except requests.RequestException:
        order.status = "failed"
        order.save(update_fields=["status"])
        return Response({"error": "Safaricom M-PESA could not be reached. Please try again."}, status=502)
    if not isinstance(result, dict) or result.get("ResponseCode") != "0":
        order.status = "failed"
        order.save(update_fields=["status"])
        details = result if isinstance(result, dict) else {}
        return Response({"error": details.get("errorMessage") or details.get("ResponseDescription") or "M-PESA could not start this payment."}, status=400)
    checkout_request_id = result.get("CheckoutRequestID")
    if not checkout_request_id:
        order.status = "failed"
        order.save(update_fields=["status"])
        return Response({"error": "Safaricom did not return a payment request ID. Please try again."}, status=502)
    order.checkout_request_id = checkout_request_id
    order.save(update_fields=["checkout_request_id"])
    return Response({
        "order": order.pk,
        "amount_kes": amount_kes,
        "message": f"Check your phone and enter your M-PESA PIN to pay KSh {amount_kes:,}.",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def mpesa_callback(request):
    callback = request.data.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    if not checkout_id:
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(checkout_request_id=checkout_id).first()
        if order and order.status == "pending":
            metadata = {
                item.get("Name"): item.get("Value")
                for item in callback.get("CallbackMetadata", {}).get("Item", [])
                if isinstance(item, dict) and item.get("Name")
            }
            if str(callback.get("ResultCode")) == "0":
                try:
                    paid_amount = int(metadata.get("Amount", 0))
                except (TypeError, ValueError):
                    paid_amount = 0
                receipt = str(metadata.get("MpesaReceiptNumber", ""))[:30]
                if paid_amount == order.payment_amount and receipt:
                    _confirm_order_payment(order, receipt)
                    if order.user.email:
                        email = order.user.email
                        email_html = branded(
                                "Thank you!",
                                f"We received your M-PESA payment {order.receipt} for {order.product.name}.",
                                "View store",
                                settings.FRONTEND_URL,
                            )
                        transaction.on_commit(
                            lambda: send_html.delay(email, "Payment received", email_html),
                            robust=True,
                        )
                else:
                    order.status = "failed"
            else:
                order.status = "cancelled" if str(callback.get("ResultCode")) == "1032" else "failed"
            order.save(update_fields=["status", "receipt"])
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


def _confirm_order_payment(order, receipt=""):
    if order.status == "pending":
        product = Product.objects.select_for_update().get(pk=order.product_id)
        product.stock = max(0, product.stock - order.qty)
        product.save(update_fields=["stock"])
        order.status = "paid"
    if receipt:
        order.receipt = receipt[:30]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_status(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status == "pending" and order.checkout_request_id and cache.add(f"mpesa:status-query:{order.pk}", True, timeout=10):
        try:
            result = mpesa.query(order.checkout_request_id)
        except (KeyError, ValueError, requests.RequestException):
            result = {}
        result_code = str(result.get("ResultCode")) if isinstance(result, dict) else ""
        if result_code == "1032":
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order.pk, user=request.user)
                if order.status == "pending":
                    order.status = "cancelled"
                    order.save(update_fields=["status"])
        elif result_code == "0":
            reported_amount = result.get("Amount")
            try:
                amount_matches = reported_amount is None or int(reported_amount) == order.payment_amount
            except (TypeError, ValueError):
                amount_matches = False
            if amount_matches:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(pk=order.pk, user=request.user)
                    if order.status == "pending":
                        _confirm_order_payment(order, result.get("MpesaReceiptNumber", ""))
                        order.save(update_fields=["status", "receipt"])
    feedback = {
        "paid": "Payment successful.",
        "cancelled": "Payment cancelled. No payment was completed.",
        "failed": "Payment failed. Please check your M-PESA phone and try again.",
    }.get(order.status, "Payment is still processing.")
    return Response({"status": order.status, "receipt": order.receipt, "feedback": feedback})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AssistantRateThrottle])
def assistant(request):
    import anthropic

    supplied_messages = request.data.get("messages")
    if not isinstance(supplied_messages, list):
        return Response({"error": "Send a list of chat messages."}, status=400)
    messages = [
        {"role": message["role"], "content": message["content"][:1200]}
        for message in supplied_messages[-12:]
        if isinstance(message, dict)
        and message.get("role") in ("user", "assistant")
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]
    if not messages or messages[-1]["role"] != "user":
        return Response({"error": "Send a message to the shopping assistant."}, status=400)
    products = Product.objects.order_by("id")[:60]
    catalog = []
    for product in products:
        price_min_kes = mpesa.kes_amount(product.price_min)
        price = f"KSh {price_min_kes:,}" if price_min_kes is not None else "price unavailable"
        catalog.append(
            f"- {product.name} ({product.subtitle}), {price}, "
            f"{', '.join(product.specs)}, {'in stock' if product.stock else 'OUT OF STOCK'}"
        )
    catalog = "\n".join(catalog)
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=700,
            system=(
                "You are TUVA's laptop shopping assistant. Recommend and compare only items in this catalog; "
                "quote prices in Kenyan shillings (KSh), be concise and honest, and suggest a stock alert "
                "for unavailable products.\n"
                f"{catalog}"
            ),
            messages=messages,
        )
    except (anthropic.APIConnectionError, anthropic.APIStatusError):
        return Response({"error": "The shopping assistant is temporarily unavailable. Please try again."}, status=503)
    return Response({"reply": response.content[0].text})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def live_chat(request):
    try:
        conversation = str(UUID(str(request.query_params.get("conversation") if request.method == "GET" else request.data.get("conversation"))))
    except (TypeError, ValueError, AttributeError):
        return Response({"error": "Start a valid chat conversation."}, status=400)
    if request.method == "GET":
        messages = list(
            ChatMessage.objects.filter(conversation=conversation).order_by("-created", "-id")[:100]
        )
        messages.reverse()
        return Response({
            "messages": [
                {"id": message.pk, "sender": message.sender, "message": message.message, "created": message.created}
                for message in messages
            ]
        })

    text = str(request.data.get("message", "")).strip()
    if not text or len(text) > 2000:
        return Response({"error": "Write a message up to 2,000 characters."}, status=400)
    message = ChatMessage.objects.create(
        conversation=conversation,
        sender="customer",
        user=request.user if request.user.is_authenticated else None,
        message=text,
    )
    return Response({"id": message.pk, "sender": message.sender, "message": message.message, "created": message.created}, status=201)
