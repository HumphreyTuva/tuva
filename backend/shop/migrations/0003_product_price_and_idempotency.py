from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0002_order_payment_foundation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField("product", "price_min", "price"),
        migrations.RenameField("product", "price_max", "compare_price"),
        migrations.AlterField("product", "compare_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.RemoveField("product", "rating"),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                condition=~models.Q(idempotency_key=""),
                fields=("user", "idempotency_key"),
                name="unique_user_checkout_idempotency",
            ),
        ),
    ]
