from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Product


@receiver(pre_save, sender=Product)
def _prev(sender, instance, **kwargs):
    existing = Product.objects.filter(pk=instance.pk).only("stock", "reserved").first() if instance.pk else None
    instance._previous_stock = existing.stock if existing else None
    instance._was_out = bool(existing and existing.stock <= existing.reserved)


@receiver(post_save, sender=Product)
def _restock(sender, instance, created, **kwargs):
    previous_stock = getattr(instance, "_previous_stock", None)
    if created and instance.stock:
        from .models import StockMovement
        StockMovement.objects.create(product=instance, quantity_delta=instance.stock, reason="import", note="Initial stock")
    elif previous_stock is not None and previous_stock != instance.stock:
        from .models import StockMovement
        movement_order = getattr(instance, "_stock_movement_order", None)
        StockMovement.objects.create(
            product=instance,
            order=movement_order,
            quantity_delta=instance.stock - previous_stock,
            reason="sale" if movement_order else "restock" if instance.stock > previous_stock else "adjustment",
            note=f"Order {movement_order.reference}" if movement_order else "Product stock updated",
        )
    if instance.available_stock > 0 and (created or getattr(instance, "_was_out", False)):
        from .models import StockAlert

        pending = StockAlert.objects.filter(notified=False)
        linked_alert = pending.filter(product=instance).exists()
        matching_query = any(
            alert.query.casefold() in instance.name.casefold() or instance.name.casefold() in alert.query.casefold()
            for alert in pending.filter(product__isnull=True).only("query")
        )
        if linked_alert or matching_query:
            from .tasks import notify_back_in_stock

            transaction.on_commit(lambda: notify_back_in_stock.delay(instance.pk), robust=True)
