import uuid
from decimal import Decimal

import django.db.models.deletion
import shop.models
from django.conf import settings
from django.db import migrations, models
from django.db.models import F


def migrate_legacy_orders(apps, schema_editor):
    Order = apps.get_model("shop", "Order")
    OrderItem = apps.get_model("shop", "OrderItem")
    MpesaPayment = apps.get_model("shop", "MpesaPayment")
    StockMovement = apps.get_model("shop", "StockMovement")
    database = schema_editor.connection.alias
    for order in Order.objects.using(database).all().iterator():
        order.reference = f"TV-{uuid.uuid4().hex[:10].upper()}"
        order.subtotal = order.amount
        order.total = order.amount
        if order.status == "paid":
            order.status = "processing"
            order.payment_status = "successful"
            order.stock_committed = True
        elif order.status == "cancelled":
            order.status = "cancelled"
            order.payment_status = "cancelled"
        elif order.status == "failed":
            order.status = "pending_payment"
            order.payment_status = "failed"
        else:
            order.status = "pending_payment"
            order.payment_status = "pending"
            order.stock_reserved = True
            Product = apps.get_model("shop", "Product")
            Product.objects.using(database).filter(pk=order.product_id).update(reserved=F("reserved") + order.qty)
        order.save(using=database, update_fields=["reference", "subtotal", "total", "status", "payment_status", "stock_reserved", "stock_committed"])
        OrderItem.objects.using(database).create(
            order_id=order.pk,
            product_id=order.product_id,
            quantity=order.qty,
            unit_price=order.amount / max(order.qty, 1),
            line_total=order.amount,
        )
        MpesaPayment.objects.using(database).create(
            order_id=order.pk,
            phone=order.phone,
            amount=order.payment_amount,
            checkout_request_id=order.checkout_request_id,
            status=order.payment_status,
            receipt=order.receipt,
        )
        if order.stock_committed:
            StockMovement.objects.using(database).create(
                product_id=order.product_id,
                order_id=order.pk,
                quantity_delta=-order.qty,
                reason="sale",
                note="Migrated paid order",
            )


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeliveryZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("fee", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=10)),
                ("eta", models.CharField(blank=True, max_length=100)),
                ("is_collection", models.BooleanField(default=False)),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField("order", "reference", models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField("order", "guest_access_token", models.CharField(blank=True, default="", max_length=64)),
        migrations.AddField("order", "idempotency_key", models.CharField(blank=True, default="", max_length=64)),
        migrations.AddField("order", "full_name", models.CharField(blank=True, max_length=150)),
        migrations.AddField("order", "email", models.EmailField(blank=True, max_length=254)),
        migrations.AddField("order", "address", models.CharField(blank=True, max_length=255)),
        migrations.AddField("order", "city", models.CharField(blank=True, max_length=100)),
        migrations.AddField("order", "delivery_label", models.CharField(blank=True, max_length=120)),
        migrations.AddField("order", "subtotal", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=10)),
        migrations.AddField("order", "delivery_fee", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=10)),
        migrations.AddField("order", "discount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=10)),
        migrations.AddField("order", "total", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=10)),
        migrations.AddField("order", "payment_method", models.CharField(choices=[("mpesa", "M-PESA"), ("cod", "Cash on delivery")], default="mpesa", max_length=8)),
        migrations.AddField("order", "payment_status", models.CharField(choices=[("pending", "Pending"), ("successful", "Successful"), ("failed", "Failed"), ("cancelled", "Cancelled"), ("reconcile", "Reconcile"), ("cod", "Cod")], db_index=True, default="pending", max_length=16)),
        migrations.AddField("order", "stock_reserved", models.BooleanField(default=False)),
        migrations.AddField("order", "stock_committed", models.BooleanField(default=False)),
        migrations.AddField("order", "delivery_zone", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="shop.deliveryzone")),
        migrations.AlterField("order", "user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        migrations.AlterField("order", "product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="shop.product")),
        migrations.AlterField("order", "status", models.CharField(choices=[("pending_payment", "Pending Payment"), ("processing", "Processing"), ("confirmed", "Confirmed"), ("ready", "Ready"), ("dispatched", "Dispatched"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], db_index=True, default="pending_payment", max_length=24)),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="shop.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="shop.product")),
            ],
        ),
        migrations.AddField("product", "reserved", models.PositiveIntegerField(default=0)),
        migrations.CreateModel(
            name="MpesaPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone", models.CharField(max_length=15)),
                ("amount", models.PositiveIntegerField()),
                ("checkout_request_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("merchant_request_id", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("successful", "Successful"), ("failed", "Failed"), ("cancelled", "Cancelled"), ("reconcile", "Reconcile")], db_index=True, default="pending", max_length=16)),
                ("receipt", models.CharField(blank=True, db_index=True, max_length=30)),
                ("result_code", models.CharField(blank=True, max_length=12)),
                ("result_desc", models.CharField(blank=True, max_length=255)),
                ("callback_count", models.PositiveIntegerField(default=0)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="shop.order")),
            ],
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity_delta", models.IntegerField()),
                ("reason", models.CharField(choices=[("restock", "Restock"), ("sale", "Sale"), ("adjustment", "Adjustment"), ("import", "Import")], default="adjustment", max_length=16)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_movements", to="shop.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_movements", to="shop.product")),
            ],
        ),
        migrations.RunPython(migrate_legacy_orders, migrations.RunPython.noop),
        migrations.AlterField("order", "reference", models.CharField(default=shop.models.new_order_reference, max_length=20, unique=True)),
    ]
