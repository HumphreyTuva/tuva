from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Product


@receiver(pre_save, sender=Product)
def _prev(sender, instance, **kwargs):
    instance._was_out = bool(instance.pk) and not Product.objects.filter(
        pk=instance.pk,
        stock__gt=0,
    ).exists()


@receiver(post_save, sender=Product)
def _restock(sender, instance, created, **kwargs):
    if instance.stock > 0 and (created or getattr(instance, "_was_out", False)):
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
