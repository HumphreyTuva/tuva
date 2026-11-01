import hmac
import os
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
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
from .models import AvailabilityRequest, ChatMessage, DeliveryZone, MpesaPayment, Order, OrderItem, Product, StockAlert
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
    try:
        offset = int(request.GET.get("offset", "0"))
    except ValueError:
        return Response({"error": "Offset must be a non-negative integer."}, status=400)
    if offset < 0:
        return Response({"error": "Offset must be a non-negative integer."}, status=400)
    queryset = Product.objects.filter(is_active=True).prefetch_related("gallery_images").order_by("id")
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(subtitle__icontains=query) | Q(category__icontains=query))
    if category:
        queryset = queryset.filter(category__iexact=category)
    if request.GET.get("include_count") == "true":
        return Response({
            "count": queryset.count(),
            "results": serialize_products(queryset[offset:offset + 48], request),
        })
    return Response(serialize_products(queryset[offset:offset + 48], request))


@api_view(["GET"])
@permission_classes([AllowAny])
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.filter(is_active=True).prefetch_related("gallery_images"),
        pk=pk,
    )
    return Response(ProductSerializer(product, context={"request": request}).data)


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
    matches = similar(
        vector,
        Product.objects.filter(is_active=True).exclude(embedding=None).prefetch_related("gallery_images").order_by("id"),
    )
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
    if request.data.get("consent") is not True:
        return Response({"error": "Consent is required to receive availability emails."}, status=400)
    product = Product.objects.filter(name__iexact=query).first()
    alert, created = AvailabilityRequest.objects.get_or_create(
        email=email, query=query, status="active",
        defaults={"consent": True, "matched_product": product,
                  "brand": str(request.data.get("brand", "")).strip()[:80]},
    )
    if created:
        send_html.delay(
            email,
            "You're on the list",
            branded("We'll let you know", f"We'll email you as soon as “{query}” is available.", "Keep browsing", settings.FRONTEND_URL),
        )
    return Response({"ok": True}, status=201 if created else 200)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def unsubscribe_alert(request, token):
    found = AvailabilityRequest.objects.filter(token=token).first()
    if not found:
        raise Http404
    if found.status != "unsubscribed":
        found.status = "unsubscribed"
        found.save(update_fields=["status"])
    return Response({"ok": True, "message": "You have been unsubscribed."})


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
def store_config(request):
    return Response({"guest_checkout": settings.ALLOW_GUEST_CHECKOUT})


@api_view(["GET"])
@permission_classes([AllowAny])
def delivery_zones(request):
    return Response(list(DeliveryZone.objects.filter(active=True).order_by("name").values(
        "id", "name", "fee", "eta", "is_collection",
    )))


@transaction.atomic
def calculate_cart_quote(items, delivery_zone_id=None):
    if not isinstance(items, list) or not items:
        return None, ["Add at least one product to your cart."]
    normalized = {}
    for row in items:
        try:
            product_id = int(row.get("product", row.get("id")))
            quantity = int(row.get("quantity", row.get("qty", 0)))
        except (AttributeError, TypeError, ValueError):
            return None, ["A cart item has an invalid product or quantity."]
        if quantity < 1 or quantity > 100:
            return None, ["Each item quantity must be between 1 and 100."]
        normalized[product_id] = normalized.get(product_id, 0) + quantity
        if normalized[product_id] > 100:
            return None, ["Each product quantity must be 100 or less."]

    products = {p.pk: p for p in Product.objects.select_for_update().filter(is_active=True, pk__in=normalized).order_by("pk")}
    issues, lines = [], []
    for product_id, quantity in normalized.items():
        product = products.get(product_id)
        if not product:
            issues.append(f"Product {product_id} is no longer available.")
            continue
        if quantity > product.available_stock:
            issues.append(f"Only {product.available_stock} unit(s) of {product.name} are available.")
        if product.price <= 0:
            issues.append(f"{product.name} does not have a valid price.")
        lines.append({"product": product, "quantity": quantity, "unit_price": product.price, "line_total": product.price * quantity})

    zone = None
    delivery_fee = Decimal("0.00")
    if delivery_zone_id not in (None, ""):
        try:
            zone = DeliveryZone.objects.filter(pk=delivery_zone_id, active=True).first()
        except (TypeError, ValueError):
            zone = None
        if not zone:
            issues.append("Choose a valid delivery zone.")
        else:
            delivery_fee = zone.fee
    subtotal = sum((line["line_total"] for line in lines), start=Decimal("0.00"))
    if issues:
        return None, issues
    total = subtotal + delivery_fee
    amount_kes = mpesa.round_kes_amount(total)
    if amount_kes is None:
        return None, ["The total is invalid for M-PESA checkout."]
    return {"items": lines, "zone": zone, "subtotal": subtotal, "delivery_fee": delivery_fee,
            "total": total, "amount_kes": amount_kes}, []


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def checkout_quote(request):
    if request.method == "POST":
        quote, issues = calculate_cart_quote(
            request.data.get("items"), request.data.get("delivery_zone"),
        )
        if issues:
            return Response({"issues": issues}, status=400)
        return Response({
            "lines": [{"product": line["product"].pk, "name": line["product"].name,
                       "quantity": line["quantity"], "unit_price": line["unit_price"], "line_total": line["line_total"]}
                      for line in quote["items"]],
            "subtotal": quote["subtotal"], "delivery_fee": quote["delivery_fee"],
            "total": quote["total"],
            "amount_kes": quote["amount_kes"], "delivery_zone": quote["zone"].name if quote["zone"] else None,
        })
    try:
        quantity = int(request.query_params.get("qty", "1"))
    except (TypeError, ValueError):
        return Response({"error": "Choose a valid quantity."}, status=400)
    quote, issues = calculate_cart_quote(
        [{"product": request.query_params.get("product"), "quantity": quantity}],
        request.query_params.get("delivery_zone"),
    )
    if issues:
        return Response({"error": "; ".join(issues), "issues": issues}, status=400)
    return Response({"amount_kes": quote["amount_kes"], "quantity": quantity,
                     "subtotal": quote["subtotal"], "delivery_fee": quote["delivery_fee"],
                     "total": quote["total"]})


@api_view(["POST"])
@permission_classes([AllowAny])
def checkout(request):
    idempotency_key = str(request.headers.get("Idempotency-Key", "")).strip()
    if idempotency_key and not 8 <= len(idempotency_key) <= 64:
        return Response({"error": "The checkout request key is invalid."}, status=400)
    items = request.data.get("items")
    if items is None:
        items = [{"product": request.data.get("product"), "quantity": request.data.get("qty", 1)}]
    if not isinstance(items, list) or not items:
        return Response({"error": "Choose at least one product."}, status=400)
    is_guest = not request.user.is_authenticated
    if is_guest and not settings.ALLOW_GUEST_CHECKOUT:
        return Response({"error": "Sign in before checkout. Guest checkout is currently disabled."}, status=401)
    guest_name = str(request.data.get("full_name", "")).strip()[:150] if is_guest else ""
    guest_email = str(request.data.get("email", "")).strip()[:254] if is_guest else ""
    if is_guest:
        if not guest_name:
            return Response({"error": "Enter your name for this order."}, status=400)
        try:
            validate_email(guest_email)
        except ValidationError:
            return Response({"error": "Enter a valid email address for this order."}, status=400)
    try:
        phone = mpesa.normalize(request.data.get("phone", ""))
    except ValueError as error:
        return Response({"error": str(error)}, status=400)

    with transaction.atomic():
        if idempotency_key:
            if not is_guest:
                get_user_model().objects.select_for_update().filter(pk=request.user.pk).only("pk").first()
            owner_orders = Order.objects.filter(user=None, email=guest_email) if is_guest else Order.objects.filter(user=request.user)
            previous = owner_orders.filter(idempotency_key=idempotency_key).first()
            if previous:
                if previous.checkout_request_id:
                    return Response({"order": previous.pk, "reference": previous.reference, "amount_kes": previous.payment_amount,
                                     **({"access_token": previous.guest_access_token} if is_guest else {}),
                                     "message": "This payment request is already in progress."})
                if previous.payment_status in {"failed", "cancelled"}:
                    return Response({"error": "The previous payment attempt failed. Start a new checkout."}, status=409)
                return Response({"order": previous.pk, "reference": previous.reference, "amount_kes": previous.payment_amount,
                                 **({"access_token": previous.guest_access_token} if is_guest else {}),
                                 "message": "This payment request is already being processed."})
        quote, issues = calculate_cart_quote(items, request.data.get("delivery_zone"))
        if issues:
            return Response({"error": "; ".join(issues), "issues": issues}, status=400)
        amount_kes = quote["amount_kes"]
        lines = quote["items"]
        first = lines[0]
        product = first["product"] if len(lines) == 1 else None
        quantity = first["quantity"] if len(lines) == 1 else sum(line["quantity"] for line in lines)
        order = Order.objects.create(
            user=request.user if not is_guest else None,
            product=product,
            qty=quantity,
            amount=quote["total"],
            payment_amount=amount_kes,
            phone=phone,
            delivery_zone=quote["zone"],
            subtotal=quote["subtotal"],
            delivery_fee=quote["delivery_fee"],
            discount=Decimal("0.00"),
            total=quote["total"],
            payment_method="mpesa",
            status="pending_payment",
            payment_status="pending",
            stock_reserved=True,
            idempotency_key=idempotency_key,
            guest_access_token=get_random_string(48) if is_guest else "",
            full_name=guest_name,
            email=guest_email,
            address=str(request.data.get("address", "")).strip()[:255],
            city=str(request.data.get("city", "")).strip()[:100],
            delivery_label=quote["zone"].name if quote["zone"] else "",
        )
        for line in lines:
            item_product = line["product"]
            item_product.reserved += line["quantity"]
            item_product.save(update_fields=["reserved"])
            OrderItem.objects.create(order=order, product=item_product, quantity=line["quantity"],
                                     unit_price=line["unit_price"], line_total=line["line_total"])
        payment = MpesaPayment.objects.create(order=order, phone=phone, amount=amount_kes)

    if settings.MPESA_SIMULATE:
        checkout_request_id = f"SIM-{order.reference}"
        order.checkout_request_id = checkout_request_id
        order.save(update_fields=["checkout_request_id"])
        payment.checkout_request_id = checkout_request_id
        payment.save(update_fields=["checkout_request_id"])
        return Response({
            "order": order.pk,
            "reference": order.reference,
            **({"access_token": order.guest_access_token} if is_guest else {}),
            "amount_kes": amount_kes,
            "message": f"Simulation: your payment will confirm in about 6 seconds (KSh {amount_kes:,}).",
        })

    try:
        result = mpesa.stk_push(phone, amount_kes, f"TUVA{order.pk}")
    except (KeyError, ValueError):
        _fail_payment(order, "failed")
        return Response({"error": "M-PESA credentials are incomplete or the phone number is invalid."}, status=503)
    except requests.RequestException:
        _fail_payment(order, "failed")
        return Response({"error": "Safaricom M-PESA could not be reached. Please try again."}, status=502)
    if not isinstance(result, dict) or result.get("ResponseCode") != "0":
        _fail_payment(order, "failed")
        details = result if isinstance(result, dict) else {}
        return Response({"error": details.get("errorMessage") or details.get("ResponseDescription") or "M-PESA could not start this payment."}, status=400)
    checkout_request_id = result.get("CheckoutRequestID")
    if not checkout_request_id:
        _fail_payment(order, "failed")
        return Response({"error": "Safaricom did not return a payment request ID. Please try again."}, status=502)
    order.checkout_request_id = checkout_request_id
    order.save(update_fields=["checkout_request_id"])
    payment.checkout_request_id = checkout_request_id
    payment.merchant_request_id = str(result.get("MerchantRequestID", ""))[:100]
    payment.save(update_fields=["checkout_request_id", "merchant_request_id"])
    return Response({
        "order": order.pk,
        "reference": order.reference,
        **({"access_token": order.guest_access_token} if is_guest else {}),
        "amount_kes": amount_kes,
        "message": f"Check your phone and enter your M-PESA PIN to pay KSh {amount_kes:,}.",
    })


def _release_order_reservation(order):
    if not order.stock_reserved or order.stock_committed:
        return
    items = list(order.items.all())
    lines = [(item.product_id, item.quantity) for item in items]
    if not lines and order.product_id:
        lines = [(order.product_id, order.qty)]
    for product_id, quantity in lines:
        product = Product.objects.select_for_update().get(pk=product_id)
        product.reserved = max(0, product.reserved - quantity)
        product.save(update_fields=["reserved"])
    order.stock_reserved = False


def _fail_payment(order, payment_status, result_code="", result_desc=""):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        _release_order_reservation(order)
        order.payment_status = payment_status
        if payment_status == "cancelled":
            order.status = "cancelled"
        order.save(update_fields=["stock_reserved", "payment_status", "status"])
        payment = MpesaPayment.objects.select_for_update().filter(order=order).order_by("-created").first()
        if payment:
            payment.status = payment_status
            payment.result_code = str(result_code)[:12]
            payment.result_desc = str(result_desc)[:255]
            payment.save(update_fields=["status", "result_code", "result_desc"])
    return order


@api_view(["POST"])
@permission_classes([AllowAny])
def mpesa_callback(request, secret):
    if not settings.MPESA_CALLBACK_SECRET or not hmac.compare_digest(secret, settings.MPESA_CALLBACK_SECRET):
        from django.http import Http404
        raise Http404
    callback = request.data.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    if not checkout_id:
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(checkout_request_id=checkout_id).first()
        if order:
            result_code = str(callback.get("ResultCode", ""))
            result_desc = str(callback.get("ResultDesc", ""))
            payment = MpesaPayment.objects.select_for_update().filter(
                order=order, checkout_request_id=checkout_id,
            ).first()
            if payment:
                payment.callback_count += 1
                payment.result_code = result_code[:12]
                payment.result_desc = result_desc[:255]
                payment.save(update_fields=["callback_count", "result_code", "result_desc"])
            if result_code == "0":
                metadata = {
                    item.get("Name"): item.get("Value")
                    for item in callback.get("CallbackMetadata", {}).get("Item", [])
                    if isinstance(item, dict) and item.get("Name")
                }
                try:
                    paid_amount = int(metadata.get("Amount", 0))
                except (TypeError, ValueError):
                    paid_amount = 0
                receipt = str(metadata.get("MpesaReceiptNumber", ""))[:30]
                duplicate_receipt = bool(receipt and MpesaPayment.objects.filter(receipt=receipt).exclude(order=order).exists())
                if order.payment_status in {"failed", "cancelled", "reconcile"}:
                    order.payment_status = "reconcile"
                    order.save(update_fields=["payment_status"])
                    if payment:
                        payment.status = "reconcile"
                        payment.save(update_fields=["status"])
                elif order.payment_status == "successful":
                    if receipt and (duplicate_receipt or (order.receipt and receipt != order.receipt)):
                        order.payment_status = "reconcile"
                        order.save(update_fields=["payment_status"])
                        if payment:
                            payment.status = "reconcile"
                            payment.save(update_fields=["status"])
                    elif receipt and not order.receipt:
                        order.receipt = receipt
                        order.save(update_fields=["receipt"])
                elif paid_amount != order.payment_amount or not receipt or duplicate_receipt:
                    order.payment_status = "reconcile"
                    order.save(update_fields=["payment_status"])
                    if payment:
                        payment.status = "reconcile"
                        payment.receipt = receipt
                        payment.save(update_fields=["status", "receipt"])
                else:
                    _confirm_order_payment(order, receipt)
                    order.save(update_fields=["status", "payment_status", "stock_reserved", "stock_committed", "receipt"])
                    if payment:
                        payment.status = "successful"
                        payment.receipt = receipt
                        payment.save(update_fields=["status", "receipt"])
                    if order.user and order.user.email:
                        email = order.user.email
                        items = list(order.items.select_related("product"))
                        item_summary = ", ".join(f"{item.product.name} × {item.quantity}" for item in items) or (order.product.name if order.product_id else "your order")
                        email_html = branded(
                            "Thank you!",
                            f"We received your M-PESA payment {order.receipt} for {item_summary}.",
                            "View store",
                            settings.FRONTEND_URL,
                        )
                        transaction.on_commit(
                            lambda: send_html.delay(email, "Payment received", email_html),
                            robust=True,
                        )
            elif order.payment_status == "pending":
                payment_status = "cancelled" if result_code == "1032" else "failed"
                _fail_payment(order, payment_status, result_code, result_desc)
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


def _confirm_order_payment(order, receipt=""):
    if order.payment_status != "successful" and not order.stock_committed:
        items = list(order.items.all())
        lines = [(item.product_id, item.quantity) for item in items]
        if not lines and order.product_id:
            lines = [(order.product_id, order.qty)]
        for product_id, quantity in lines:
            product = Product.objects.select_for_update().get(pk=product_id)
            if order.stock_reserved:
                product.reserved = max(0, product.reserved - quantity)
            product.stock = max(0, product.stock - quantity)
            product._stock_movement_order = order
            product.save(update_fields=["stock", "reserved"])
        order.stock_reserved = False
        order.stock_committed = True
    order.payment_status = "successful"
    order.status = "processing"
    if receipt:
        order.receipt = receipt[:30]


@api_view(["GET"])
@permission_classes([AllowAny])
def order_status(request, pk):
    if request.user.is_authenticated:
        owner_filter = {"user": request.user}
    else:
        guest_token = str(request.headers.get("X-Order-Access-Token", ""))
        owner_filter = {"user__isnull": True}
        order = get_object_or_404(Order, pk=pk, **owner_filter)
        if not guest_token or not hmac.compare_digest(guest_token, order.guest_access_token):
            raise Http404
    order = get_object_or_404(Order, pk=pk, **owner_filter)
    if settings.MPESA_SIMULATE and order.payment_status == "pending" and order.created <= timezone.now() - timedelta(seconds=6):
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk, **owner_filter)
            if order.payment_status == "pending":
                receipt = f"SIM{order.reference[-10:]}"
                _confirm_order_payment(order, receipt)
                order.save(update_fields=["status", "payment_status", "stock_reserved", "stock_committed", "receipt"])
                MpesaPayment.objects.filter(order=order, checkout_request_id=order.checkout_request_id).update(
                    status="successful", receipt=receipt,
                )
    elif order.payment_status == "pending" and order.checkout_request_id and order.created <= timezone.now() - timedelta(seconds=25) and Order.objects.filter(
        pk=order.pk, payment_status="pending",
    ).filter(Q(last_status_query_at__isnull=True) | Q(last_status_query_at__lte=timezone.now() - timedelta(seconds=10))).update(
        last_status_query_at=timezone.now(),
    ):
        try:
            result = mpesa.query(order.checkout_request_id)
        except (KeyError, ValueError, requests.RequestException):
            result = {}
        result_code = str(result.get("ResultCode") or "") if isinstance(result, dict) else ""
        if result_code == "1032":
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order.pk, **owner_filter)
                if order.payment_status == "pending":
                    order = _fail_payment(order, "cancelled", result_code, str(result.get("ResultDesc", "")))
        elif result_code == "0":
            reported_amount = result.get("Amount")
            try:
                amount_matches = reported_amount is not None and int(reported_amount) == order.payment_amount
            except (TypeError, ValueError):
                amount_matches = False
            receipt = str(result.get("MpesaReceiptNumber", ""))[:30]
            receipt_duplicate = bool(receipt and MpesaPayment.objects.filter(receipt=receipt).exclude(order=order).exists())
            if amount_matches and receipt and not receipt_duplicate:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(pk=order.pk, **owner_filter)
                    if order.payment_status == "pending":
                        _confirm_order_payment(order, receipt)
                        order.save(update_fields=["status", "payment_status", "stock_reserved", "stock_committed", "receipt"])
                        MpesaPayment.objects.filter(order=order, checkout_request_id=order.checkout_request_id).update(
                            status="successful", receipt=order.receipt,
                        )
            elif not amount_matches or not receipt or receipt_duplicate:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(pk=order.pk, **owner_filter)
                    if order.payment_status == "pending":
                        order.payment_status = "reconcile"
                        order.save(update_fields=["payment_status"])
                        MpesaPayment.objects.filter(order=order, checkout_request_id=order.checkout_request_id).update(status="reconcile")
        elif result_code == "1037":
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order.pk, **owner_filter)
                if order.payment_status == "pending":
                    order = _fail_payment(order, "failed", result_code, str(result.get("ResultDesc", "")))
        elif result_code:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order.pk, **owner_filter)
                if order.payment_status == "pending":
                    order = _fail_payment(order, "failed", result_code, str(result.get("ResultDesc", "")))
    feedback = {
        "processing": "Payment successful. Your order is being prepared.",
        "cancelled": "Payment cancelled. No payment was completed.",
    }.get(order.status, "Payment is still processing.")
    if order.payment_status == "failed":
        feedback = "Payment failed. Please check your M-PESA phone and try again."
    elif order.payment_status == "reconcile":
        feedback = "Your payment needs review. Please contact TUVA support before trying again."
    return Response({"status": order.status, "payment_status": order.payment_status, "receipt": order.receipt, "feedback": feedback})


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
    products = Product.objects.filter(is_active=True, stock__gt=0).order_by("id")[:60]
    catalog = []
    for product in products:
        price_min_kes = mpesa.round_kes_amount(product.price_min)
        price = f"KSh {price_min_kes:,}" if price_min_kes is not None else "price unavailable"
        catalog.append(
            f"- {product.name} ({product.subtitle}), {price}, "
            f"{', '.join(product.specs)}, {'in stock' if product.available_stock else 'OUT OF STOCK'}"
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
