import django.utils.timezone
import django.utils.crypto
from django.db import migrations, models
import django.db.models.deletion
import shop.models


def preserve_legacy_alerts_without_assumed_consent(apps, schema_editor):
    Legacy = apps.get_model("shop", "StockAlert")
    Request = apps.get_model("shop", "AvailabilityRequest")
    database = schema_editor.connection.alias
    for old in Legacy.objects.using(database).all().iterator():
        Request.objects.using(database).create(
            email=old.email,
            query=old.query,
            consent=False,
            status="unsubscribed",
            matched_product_id=old.product_id,
            notified_at=old.created if old.notified else None,
        )


class Migration(migrations.Migration):
    dependencies = [("shop", "0006_order_query_throttle")]

    operations = [
        migrations.AddField("product", "brand", models.CharField(blank=True, db_index=True, max_length=80)),
        migrations.AddField("product", "model", models.CharField(blank=True, db_index=True, max_length=120)),
        migrations.AddField("product", "sku", models.CharField(blank=True, db_index=True, max_length=64)),
        migrations.AddField("product", "aliases", models.JSONField(blank=True, default=list)),
        migrations.CreateModel(
            name="AvailabilityRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("query", models.CharField(max_length=200)),
                ("brand", models.CharField(blank=True, max_length=80)),
                ("reference_url", models.URLField(blank=True, max_length=500)),
                ("notes", models.CharField(blank=True, max_length=500)),
                ("consent", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("active", "Active"), ("notified", "Notified"), ("unsubscribed", "Unsubscribed")], db_index=True, default="active", max_length=16)),
                ("token", models.CharField(default=shop.models.new_availability_token, max_length=64, unique=True)),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("notified_at", models.DateTimeField(blank=True, null=True)),
                ("matched_product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="shop.product")),
            ],
        ),
        migrations.CreateModel(
            name="EmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(db_index=True, max_length=40)),
                ("to_email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=200)),
                ("html", models.TextField()),
                ("text", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"), ("failed", "Failed")], db_index=True, default="pending", max_length=12)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("error", models.TextField(blank=True)),
                ("dedupe_key", models.CharField(max_length=160, unique=True)),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("availability_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="shop.availabilityrequest")),
            ],
        ),
        migrations.RunPython(preserve_legacy_alerts_without_assumed_consent, migrations.RunPython.noop),
    ]
