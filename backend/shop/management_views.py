from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .imagesearch import embed
from .imageopt import optimize_upload
from .models import ChatMessage, Order, Product, ProductImage, StockAlert
from .serializers import ProductSerializer
from .views import serialize_products
from rest_framework.authtoken.models import Token


class AdminLoginThrottle(SimpleRateThrottle):
    scope = "admin_login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AdminLoginThrottle])
def admin_login(request):
    username = str(request.data.get("username", "")).strip()[:150]
    password = request.data.get("password", "")
    if not username or not isinstance(password, str) or not password:
        return Response({"error": "Enter your staff username and password."}, status=400)

    user = authenticate(request, username=username, password=password)
    if not user or not user.is_staff:
        return Response({"error": "Invalid staff credentials."}, status=401)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "name": user.get_short_name() or user.username})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_dashboard(request):
    active_products = Product.objects.filter(is_active=True)
    products = active_products.prefetch_related("gallery_images").order_by("name", "id")[:100]
    orders = Order.objects.select_related("product", "user").prefetch_related("items__product").order_by("-created", "-id")[:10]
    alerts = StockAlert.objects.filter(notified=False).order_by("-created", "-id")[:10]

    conversations = {}
    recent_messages = ChatMessage.objects.order_by("-created", "-id")[:500]
    for message in recent_messages:
        key = str(message.conversation)
        if key not in conversations:
            conversations[key] = {
                "conversation": key,
                "message": message.message,
                "sender": message.sender,
                "updated": message.created,
                "message_count": 0,
            }
        conversations[key]["message_count"] += 1
    conversation_list = list(conversations.values())[:12]

    paid_revenue = Order.objects.filter(payment_status="successful").aggregate(total=Sum("total"))["total"] or 0
    return Response({
        "metrics": {
            "products": active_products.count(),
            "in_stock": active_products.filter(stock__gt=F("reserved")).count(),
            "low_stock": active_products.filter(stock__gt=0, stock__lte=5).count(),
            "orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(payment_status="pending").count(),
            "paid_revenue": paid_revenue,
            "open_alerts": StockAlert.objects.filter(notified=False).count(),
        },
        "products": serialize_products(products, request),
        "orders": [
            {
                "id": order.pk,
                "product": ", ".join(f"{item.product.name} × {item.quantity}" for item in order.items.all()) or (order.product.name if order.product_id else "—"),
                "customer": order.email or ((order.user.email or order.user.username) if order.user else "Guest"),
                "quantity": sum(item.quantity for item in order.items.all()) or order.qty,
                "amount": order.total or order.amount,
                "payment_amount": order.payment_amount,
                "status": order.status,
                "payment_status": order.payment_status,
                "reference": order.reference,
                "created": order.created,
            }
            for order in orders
        ],
        "alerts": [
            {
                "id": alert.pk,
                "email": alert.email,
                "query": alert.query,
                "created": alert.created,
            }
            for alert in alerts
        ],
        "conversations": conversation_list,
    })


@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def admin_update_stock(request, pk):
    stock = request.data.get("stock")
    if isinstance(stock, bool) or not isinstance(stock, int) or not 0 <= stock <= 1_000_000:
        return Response({"error": "Stock must be a whole number between 0 and 1,000,000."}, status=400)

    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        old_stock = product.stock
        if stock < product.reserved:
            return Response({"error": f"{product.reserved} unit(s) are reserved for active orders."}, status=400)
        if stock == old_stock:
            return Response({"id": product.pk, "stock": product.stock})
        product.stock = stock
        product.save(update_fields=["stock"])
    cache.clear()
    return Response({"id": product.pk, "stock": product.stock, "available_stock": product.available_stock})


@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def admin_products(request):
    if request.method == "GET":
        query = request.query_params.get("q", "").strip()[:120]
        try:
            offset = int(request.query_params.get("offset", "0"))
        except ValueError:
            return Response({"error": "Offset must be a non-negative integer."}, status=400)
        if offset < 0:
            return Response({"error": "Offset must be a non-negative integer."}, status=400)

        products = Product.objects.filter(is_active=True).prefetch_related("gallery_images").order_by("name", "id")
        if query:
            products = products.filter(
                Q(name__icontains=query)
                | Q(subtitle__icontains=query)
                | Q(category__icontains=query)
                | Q(use_cases__icontains=query)
                | Q(brand__icontains=query)
                | Q(model__icontains=query)
                | Q(sku__icontains=query)
            )
        count = products.count()
        return Response({
            "count": count,
            "results": serialize_products(products[offset:offset + 50], request),
        })

    serializer = ProductSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    product = serializer.save()
    cache.clear()
    return Response(ProductSerializer(product, context={"request": request}).data, status=201)


@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def admin_update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product, data=request.data, partial=True, context={"request": request})
    serializer.is_valid(raise_exception=True)
    product = serializer.save()
    cache.clear()
    return Response(ProductSerializer(product, context={"request": request}).data)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAdminUser])
def admin_manage_product_image(request, pk, image_id):
    product = get_object_or_404(Product.objects.prefetch_related("gallery_images"), pk=pk)
    if image_id == "primary":
        image = product.image
        gallery_image = None
    else:
        if not image_id.isdigit():
            return Response({"error": "This product image was not found."}, status=404)
        gallery_image = get_object_or_404(ProductImage, product=product, pk=int(image_id))
        image = gallery_image.image

    if request.method == "PATCH":
        image_upload = request.FILES.get("image")
        if image_upload is None:
            return Response({"error": "Choose an image to upload."}, status=400)
        uploaded_image = serializers.ImageField().run_validation(image_upload)
        uploaded_image.seek(0)
        embedding = embed(uploaded_image) if image_id == "primary" else None
        uploaded_image.seek(0)
        stored_image = optimize_upload(uploaded_image, uploaded_image.name) or uploaded_image
        previous_name = image.name
        image.save(stored_image.name, stored_image, save=False)
        if gallery_image:
            gallery_image.save(update_fields=["image"])
        else:
            product.embedding = embedding
            product.save(update_fields=["image", "embedding"])
        if previous_name and previous_name != image.name:
            storage = image.storage
            transaction.on_commit(lambda: storage.delete(previous_name))
    else:
        image_count = int(bool(product.image)) + product.gallery_images.count()
        if image_count <= 1:
            return Response({"error": "A product must have at least one image."}, status=400)

        if gallery_image:
            image_name = gallery_image.image.name
            storage = gallery_image.image.storage
            gallery_image.delete()
        else:
            replacement = product.gallery_images.first()
            image_name = product.image.name
            storage = product.image.storage
            product.image = replacement.image.name
            product.embedding = embed(replacement.image.path)
            product.save(update_fields=["image", "embedding"])
            replacement.delete()
        transaction.on_commit(lambda: storage.delete(image_name))

    cache.clear()
    product.refresh_from_db()
    return Response(ProductSerializer(product, context={"request": request}).data)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save(update_fields=["is_active"])
    cache.clear()
    return Response(status=204)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_conversation(request, conversation):
    if not ChatMessage.objects.filter(conversation=conversation).exists():
        return Response({"error": "This support conversation was not found."}, status=404)
    messages = list(
        ChatMessage.objects.filter(conversation=conversation).order_by("-created", "-id")[:100]
    )
    messages.reverse()
    return Response({
        "messages": [
            {
                "id": message.pk,
                "sender": message.sender,
                "message": message.message,
                "created": message.created,
            }
            for message in messages
        ]
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_reply(request, conversation):
    if not ChatMessage.objects.filter(conversation=conversation).exists():
        return Response({"error": "This support conversation was not found."}, status=404)
    text = str(request.data.get("message", "")).strip()
    if not text or len(text) > 2000:
        return Response({"error": "Write a message up to 2,000 characters."}, status=400)

    message = ChatMessage.objects.create(
        conversation=conversation,
        user=request.user,
        sender="support",
        message=text,
    )
    return Response({
        "id": message.pk,
        "sender": message.sender,
        "message": message.message,
        "created": message.created,
    }, status=201)
