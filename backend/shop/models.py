from django.conf import settings
from django.db import models
import uuid
class Product(models.Model):
    name = models.CharField(max_length=120, db_index=True)
    subtitle = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=40, db_index=True)
    price_min = models.DecimalField(max_digits=10, decimal_places=2)
    price_max = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.FloatField(default=4.5)
    specs = models.JSONField(default=list)
    image = models.ImageField(upload_to="products/")
    stock = models.PositiveIntegerField(default=0)
    embedding = models.JSONField(null=True, blank=True, editable=False)
    badge = models.CharField(max_length=30, blank=True)
    @property
    def price(self):
        return self.price_min
    def save(self, *a, **k):
        super().save(*a, **k)
        if self.image and self.embedding is None:
            from .imagesearch import embed
            self.embedding = embed(self.image.path); super().save(update_fields=["embedding"])
    def __str__(self): return self.name
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT); qty = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_amount = models.PositiveIntegerField(default=0)
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=12, default="pending", db_index=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    receipt = models.CharField(max_length=30, blank=True); created = models.DateTimeField(auto_now_add=True)
