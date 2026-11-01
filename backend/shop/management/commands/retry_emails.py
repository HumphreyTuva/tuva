from django.core.management.base import BaseCommand
from shop.models import EmailLog
from shop.tasks import deliver_email_log


class Command(BaseCommand):
    help = "Retry queued or failed email deliveries, up to five total attempts."

    def handle(self, *args, **options):
        ids = list(EmailLog.objects.filter(status__in=["pending", "failed"], attempts__lt=5).order_by("created").values_list("pk", flat=True))
        sent = sum(bool(deliver_email_log(pk)) for pk in ids)
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} of {len(ids)} eligible email(s)."))
