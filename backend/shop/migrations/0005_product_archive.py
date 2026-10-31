from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("shop", "0004_discount_code")]

    operations = [
        migrations.AddField("product", "is_active", models.BooleanField(default=True)),
    ]
