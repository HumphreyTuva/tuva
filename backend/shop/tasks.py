from html import escape
from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q


def branded(title, body, cta_label, cta_url):
    safe_title = escape(title)
    safe_body = escape(body)
    safe_label = escape(cta_label)
    safe_url = escape(cta_url, quote=True)
    return f'''<div style="background:#fbf7f3;padding:24px;font-family:Arial,sans-serif"><div style="max-width:520px;margin:auto;background:#fff;border-radius:16px;overflow:hidden">
<div style="padding:20px 24px;font-size:28px;font-weight:800;letter-spacing:1px">TUV<span style="color:#ff5a00">A</span></div>
<div style="padding:0 24px 24px"><h2 style="margin:0 0 8px">{safe_title}</h2><p style="color:#555;line-height:1.5">{safe_body}</p>
<a href="{safe_url}" style="display:inline-block;background:#ff5a00;color:#fff;padding:12px 22px;border-radius:8px;text-decoration:none;font-weight:700">{safe_label}</a></div>
<div style="background:#fff3ea;padding:12px 24px;font-size:12px;color:#888">Verified suppliers · Trade protection · Secure payments</div></div></div>'''


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_html(self, to, subject, html):
    try:
        message = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, [to])
        message.attach_alternative(html, "text/html")
        message.send()
    except Exception as error:
        raise self.retry(exc=error)


@shared_task
def notify_back_in_stock(product_id):
    from .models import Product, StockAlert

    product = Product.objects.get(pk=product_id)
    candidates = StockAlert.objects.filter(notified=False).filter(
        Q(product_id=product_id) | Q(product__isnull=True)
    )
    for alert in candidates:
        if (
            alert.product_id is None
            and alert.query.casefold() not in product.name.casefold()
            and product.name.casefold() not in alert.query.casefold()
        ):
            continue
        url = f"{settings.FRONTEND_URL}/?{urlencode({'q': product.name})}"
        send_html.delay(
            alert.email,
            f"{product.name} is back in stock",
            branded(
                f"{product.name} is back",
                "The laptop you were looking for is available again. Grab it before it sells out.",
                "View product",
                url,
            ),
        )
        alert.notified = True
        alert.save(update_fields=["notified"])
