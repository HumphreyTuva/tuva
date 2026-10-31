from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string
import uuid


def new_order_reference():
    return f"TV-{get_random_string(10).upper()}"
class Product(models.Model):
    name = models.CharField(max_length=120, db_index=True)
    subtitle = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=40, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    specs = models.JSONField(default=list)
    image = models.ImageField(upload_to="products/")
    stock = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    embedding = models.JSONField(null=True, blank=True, editable=False)
    badge = models.CharField(max_length=30, blank=True)
    # Compatibility aliases for the existing storefront and older clients.
    @property
    def price_min(self): return self.price
    @property
    def price_max(self): return self.compare_price if self.compare_price is not None else self.price
    def save(self, *a, **k):
        super().save(*a, **k)
        if self.image and self.embedding is None:
            from .imagesearch import embed
            self.embedding = embed(self.image.path); super().save(update_fields=["embedding"])
    def __str__(self): return self.name

    @property
    def available_stock(self):
        return max(0, self.stock - self.reserved)
class StockAlert(models.Model):
    email = models.EmailField(); query = models.CharField(max_length=200)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    notified = models.BooleanField(default=False); created = models.DateTimeField(auto_now_add=True)
class ChatMessage(models.Model):
    SENDER_CHOICES = [("customer", "Customer"), ("support", "Support")]
    conversation = models.UUIDField(default=uuid.uuid4, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, default="customer")
    message = models.CharField(max_length=2000)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ["created", "id"]
    def __str__(self): return f"{self.sender}: {self.message[:60]}"
class Order(models.Model):
    STATUS_CHOICES = [(value, value.replace("_", " ").title()) for value in (
        "pending_payment", "processing", "confirmed", "ready", "dispatched", "delivered", "cancelled",
    )]
    PAYMENT_STATUS_CHOICES = [(value, value.title()) for value in (
        "pending", "successful", "failed", "cancelled", "reconcile", "cod",
    )]
    PAYMENT_METHOD_CHOICES = [("mpesa", "M-PESA"), ("cod", "Cash on delivery")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT); qty = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_amount = models.PositiveIntegerField(default=0)
    phone = models.CharField(max_length=15)
    reference = models.CharField(max_length=20, unique=True, default=new_order_reference)
    idempotency_key = models.CharField(max_length=64, blank=True, default="")
    guest_access_token = models.CharField(max_length=64, blank=True, default="")
    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    delivery_zone = models.ForeignKey("DeliveryZone", null=True, blank=True, on_delete=models.SET_NULL)
    delivery_label = models.CharField(max_length=120, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=8, choices=PAYMENT_METHOD_CHOICES, default="mpesa")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="pending_payment", db_index=True)
    payment_status = models.CharField(max_length=16, choices=PAYMENT_STATUS_CHOICES, default="pending", db_index=True)
    stock_reserved = models.BooleanField(default=False)
    stock_committed = models.BooleanField(default=False)
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    last_status_query_at = models.DateTimeField(null=True, blank=True)
    receipt = models.CharField(max_length=30, blank=True); created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["user", "idempotency_key"],
            condition=~models.Q(idempotency_key=""),
            name="unique_user_checkout_idempotency",
        )]


class DeliveryZone(models.Model):
    name = models.CharField(max_length=100, unique=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    eta = models.CharField(max_length=100, blank=True)
    is_collection = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self): return self.name


class DiscountCode(models.Model):
    PERCENT = "percent"
    FIXED = "fixed"
    code = models.CharField(max_length=40, unique=True)
    kind = models.CharField(max_length=8, choices=[(PERCENT, "Percent"), (FIXED, "Fixed amount")], default=PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self): return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)


class MpesaPayment(models.Model):
    STATUS_CHOICES = [(value, value.title()) for value in ("pending", "successful", "failed", "cancelled", "reconcile")]
    order = models.ForeignKey(Order, related_name="payments", on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    amount = models.PositiveIntegerField()
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    receipt = models.CharField(max_length=30, blank=True, db_index=True)
    result_code = models.CharField(max_length=12, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    callback_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

class StockMovement(models.Model):
    REASONS = [(value, value.title()) for value in ("restock", "sale", "adjustment", "import")]
    product = models.ForeignKey(Product, related_name="stock_movements", on_delete=models.PROTECT)
    order = models.ForeignKey(Order, null=True, blank=True, related_name="stock_movements", on_delete=models.SET_NULL)
    quantity_delta = models.IntegerField()
    reason = models.CharField(max_length=16, choices=REASONS, default="adjustment")
    note = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
