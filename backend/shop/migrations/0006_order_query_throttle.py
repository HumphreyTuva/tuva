from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("shop", "0005_product_archive")]

    operations = [
        migrations.AddField("order", "last_status_query_at", models.DateTimeField(blank=True, null=True)),
    ]
