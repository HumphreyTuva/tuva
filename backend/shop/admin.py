from django.contrib import admin
from .models import ChatMessage, DeliveryZone, DiscountCode, MpesaPayment, Order, OrderItem, Product, StockAlert, StockMovement

admin.site.register([DeliveryZone, DiscountCode, MpesaPayment, OrderItem, StockMovement])


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("created", "conversation", "sender", "user", "message")
    list_filter = ("sender", "created")
    search_fields = ("conversation", "user__email", "message")
    readonly_fields = ("created",)
    ordering = ("created",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "display_price", "stock", "badge")
    list_filter = ("category", "badge")
    search_fields = ("name", "subtitle", "category")

    @admin.display(description="Price (Ksh)")
    def display_price(self, obj):
        return f"Ksh {obj.price:,.0f}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "qty", "display_amount", "display_payment", "status", "created")
    list_filter = ("status", "created")
    search_fields = ("user__email", "user__username", "product__name", "phone", "receipt")

    @admin.display(description="Amount (Ksh)")
    def display_amount(self, obj):
        return f"Ksh {obj.amount:,.0f}"

    @admin.display(description="Payment (Ksh)")
    def display_payment(self, obj):
        return f"Ksh {obj.payment_amount:,}" if obj.payment_amount else "—"


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("email", "query", "product", "notified", "created")
    list_filter = ("notified", "created")
    search_fields = ("email", "query")
