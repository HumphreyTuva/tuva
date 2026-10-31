from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("shop", "0003_product_price_and_idempotency")]

    operations = [
        migrations.CreateModel(
            name="DiscountCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("kind", models.CharField(choices=[("percent", "Percent"), ("fixed", "Fixed amount")], default="percent", max_length=8)),
                ("value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("active", models.BooleanField(default=True)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
