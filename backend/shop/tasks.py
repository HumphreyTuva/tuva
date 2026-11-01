from html import escape
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F

from .models import AvailabilityRequest, EmailLog

try:
    from celery import shared_task
except ImportError:  # Celery is optional when EMAIL_USE_CELERY is disabled.
    def shared_task(*args, **kwargs):
        def decorate(function):
            return function
        return decorate


def branded(title, body, cta_label, cta_url, unsubscribe_url=""):
    safe_title = escape(title)
    safe_body = escape(body)
    safe_label = escape(cta_label)
    safe_url = escape(cta_url, quote=True)
    safe_unsubscribe = escape(unsubscribe_url, quote=True)
    logo_url = escape(f"{settings.SITE_URL}/logo.png", quote=True)
    unsubscribe = (
        f'<p style="margin:18px 0 0;font-size:12px;color:#777">'
        f'<a href="{safe_unsubscribe}" style="color:#666">Unsubscribe from availability emails</a></p>'
        if safe_unsubscribe else ""
    )
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fbf7f3;font-family:Arial,sans-serif;color:#191919;padding:24px">
<tr><td align="center"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#fff;border-radius:14px;overflow:hidden">
<tr><td style="padding:22px 26px;border-bottom:1px solid #eee"><img src="{logo_url}" width="116" alt="TUVA Computers" style="display:block;width:116px;height:auto;border:0"></td></tr>
<tr><td style="padding:24px 26px"><h1 style="font-size:23px;line-height:1.25;margin:0 0 12px">{safe_title}</h1><p style="font-size:15px;line-height:1.55;color:#514b45;margin:0 0 22px">{safe_body}</p>
<a href="{safe_url}" style="display:inline-block;background:#ff5a00;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:700">{safe_label}</a>{unsubscribe}</td></tr>
<tr><td style="background:#f7f5f2;padding:14px 26px;font-size:12px;line-height:1.5;color:#777">TUVA Computers · Kenya</td></tr>
</table></td></tr></table>'''


def queue_email(*, kind, to_email, subject, html, text, dedupe_key, availability_request=None):
    if not to_email:
        return None
    with transaction.atomic():
        log, created = EmailLog.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults={
                "kind": kind, "to_email": to_email, "subject": subject,
                "html": html, "text": text, "availability_request": availability_request,
            },
        )
        if created:
            transaction.on_commit(lambda: _dispatch_email(log.pk), robust=True)
    return log


def _dispatch_email(log_id):
    if settings.EMAIL_USE_CELERY:
        try:
            deliver_email_log_task.delay(log_id)
            return
        except Exception:
            # A missing broker must never break checkout or alert subscription.
            pass
    if settings.EMAIL_ASYNC:
        Thread(target=deliver_email_log, args=(log_id,), daemon=True, name=f"tuva-email-{log_id}").start()
    else:
        deliver_email_log(log_id)


def deliver_email_log(log_id):
    claimed = EmailLog.objects.filter(
        pk=log_id, status__in=["pending", "failed"], attempts__lt=5,
    ).update(status="sending", attempts=F("attempts") + 1, error="")
    if not claimed:
        return False
    log = EmailLog.objects.get(pk=log_id)
    try:
        message = EmailMultiAlternatives(
            log.subject, log.text or log.subject, settings.DEFAULT_FROM_EMAIL, [log.to_email],
        )
        message.attach_alternative(log.html, "text/html")
        message.send(fail_silently=False)
    except Exception as error:
        EmailLog.objects.filter(pk=log_id).update(status="failed", error=str(error)[:2000])
        return False
    with transaction.atomic():
        EmailLog.objects.filter(pk=log_id).update(status="sent", error="")
        if log.availability_request_id:
            AvailabilityRequest.objects.filter(
                pk=log.availability_request_id, status="active",
            ).update(status="notified", notified_at=__import__("django.utils.timezone", fromlist=["now"]).now())
    return True


@shared_task
def deliver_email_log_task(log_id):
    return deliver_email_log(log_id)


def send_html(to_email, subject, html, *, kind="transactional", dedupe_key=None, text=""):
    return queue_email(
        kind=kind, to_email=to_email, subject=subject, html=html,
        text=text or subject, dedupe_key=dedupe_key or f"{kind}:{to_email}:{subject}",
    )


# Keep older call sites working while they migrate from Celery's .delay API.
send_html.delay = send_html


def notify_availability_request(request_id, product):
    request = AvailabilityRequest.objects.filter(pk=request_id, status="active", consent=True).first()
    if not request:
        return None
    unsubscribe_url = f"{settings.SITE_URL}/api/alerts/unsubscribe/{request.token}/"
    url = f"{settings.FRONTEND_URL}/?q={product.name}"
    html = branded(
        f"{product.name} is available", "The item you asked about is back in stock.",
        "View product", url, unsubscribe_url=unsubscribe_url,
    )
    return queue_email(
        kind="availability", to_email=request.email, subject=f"{product.name} is back in stock",
        html=html, text=f"{product.name} is back in stock. Visit {url}\nUnsubscribe: {unsubscribe_url}",
        dedupe_key=f"availability:{request.pk}:{product.pk}", availability_request=request,
    )

