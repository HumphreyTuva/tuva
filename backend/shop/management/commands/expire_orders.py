from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import requests

from shop import mpesa
from shop.models import MpesaPayment, Order
from shop.views import _confirm_order_payment, _fail_payment


class Command(BaseCommand):
    help = "Query old pending M-PESA checkouts, then close confirmed unpaid orders and release stock."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=20)
        orders = Order.objects.filter(
            payment_status="pending", payment_method="mpesa", created__lt=cutoff,
        ).exclude(checkout_request_id="")
        checked = expired = reconciled = 0
        for candidate in orders.iterator():
            try:
                result = mpesa.query(candidate.checkout_request_id)
            except (KeyError, ValueError, requests.RequestException):
                # A transient query error is not evidence that payment failed.
                continue
            if not isinstance(result, dict) or result.get("ResultCode") is None:
                continue
            checked += 1
            code = str(result.get("ResultCode"))
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=candidate.pk)
                if order.payment_status != "pending":
                    continue
                if code == "0":
                    try:
                        amount = int(result.get("Amount"))
                    except (TypeError, ValueError):
                        amount = 0
                    receipt = str(result.get("MpesaReceiptNumber", ""))[:30]
                    duplicate = bool(receipt and MpesaPayment.objects.filter(receipt=receipt).exclude(order=order).exists())
                    if amount == order.payment_amount and receipt and not duplicate:
                        _confirm_order_payment(order, receipt)
                        order.save(update_fields=["status", "payment_status", "stock_reserved", "stock_committed", "receipt"])
                        MpesaPayment.objects.filter(order=order, checkout_request_id=order.checkout_request_id).update(
                            status="successful", receipt=receipt,
                        )
                    else:
                        order.payment_status = "reconcile"
                        order.save(update_fields=["payment_status"])
                        MpesaPayment.objects.filter(order=order, checkout_request_id=order.checkout_request_id).update(status="reconcile")
                        reconciled += 1
                elif code == "1032":
                    _fail_payment(order, "cancelled", code, str(result.get("ResultDesc", "")))
                    expired += 1
                else:
                    _fail_payment(order, "failed", code, str(result.get("ResultDesc", "")))
                    expired += 1
        self.stdout.write(self.style.SUCCESS(
            f"Queried {checked} order(s); expired {expired}; sent {reconciled} to reconciliation."
        ))
