from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db.models.deletion import ProtectedError
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import ChatMessage, Order, Product, StockAlert
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
    products = Product.objects.order_by("name", "id")[:100]
    orders = Order.objects.select_related("product", "user").order_by("-created", "-id")[:10]
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

    paid_revenue = Order.objects.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
    return Response({
        "metrics": {
            "products": Product.objects.count(),
            "in_stock": Product.objects.filter(stock__gt=0).count(),
            "low_stock": Product.objects.filter(stock__gt=0, stock__lte=5).count(),
            "orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(status="pending").count(),
            "paid_revenue": paid_revenue,
            "open_alerts": StockAlert.objects.filter(notified=False).count(),
        },
        "products": serialize_products(products, request),
        "orders": [
            {
                "id": order.pk,
                "product": order.product.name,
                "customer": order.user.email or order.user.username,
                "quantity": order.qty,
                "amount": order.amount,
                "payment_amount": order.payment_amount,
                "status": order.status,
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

    product = get_object_or_404(Product, pk=pk)
    product.stock = stock
    product.save(update_fields=["stock"])
    cache.clear()
    return Response({"id": product.pk, "stock": product.stock})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_create_product(request):
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


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
    except ProtectedError:
        return Response(
            {"error": "This product cannot be deleted because it has existing orders."},
            status=409,
        )
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
