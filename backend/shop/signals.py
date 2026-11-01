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
    if instance.available_stock > 0 and not created and getattr(instance, "_was_out", False):
        from .models import AvailabilityRequest
        from .tasks import notify_availability_request

        searchable = " ".join([
            instance.name, instance.subtitle, instance.brand, instance.model, instance.sku,
            instance.category, " ".join(str(alias) for alias in (instance.aliases or [])),
        ]).casefold()
        requests = AvailabilityRequest.objects.filter(status="active", consent=True)
        for alert in requests.iterator():
            identifiers = {instance.sku.casefold(), instance.model.casefold()}
            identifiers.discard("")
            query = alert.query.strip().casefold()
            exact = query in identifiers
            tokens = [token for token in query.split() if len(token) > 1]
            matches = exact or bool(tokens) and all(token in searchable for token in tokens)
            if alert.brand and alert.brand.casefold() not in instance.brand.casefold():
                matches = False
            if matches:
                transaction.on_commit(
                    lambda request_id=alert.pk, product=instance: notify_availability_request(request_id, product),
                    robust=True,
                )
