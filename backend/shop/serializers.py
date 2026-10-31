from rest_framework import serializers
from . import mpesa
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    price_min = serializers.DecimalField(source="price", max_digits=10, decimal_places=2, read_only=True)
    price_max = serializers.DecimalField(source="compare_price", max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    price_min_kes = serializers.SerializerMethodField()
    price_max_kes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "subtitle", "category", "price", "compare_price", "price_min", "price_max",
            "price_min_kes", "price_max_kes", "specs", "image",
            "stock", "in_stock", "badge", "is_active",
        ]

    def get_in_stock(self, o): return o.available_stock > 0

    def get_price_min_kes(self, o):
        return mpesa.round_kes_amount(o.price_min)

    def get_price_max_kes(self, o):
        return mpesa.round_kes_amount(o.compare_price) if o.compare_price is not None else None

    def validate_stock(self, value):
        if value > 1_000_000:
            raise serializers.ValidationError("Stock must be between 0 and 1,000,000.")
        return value

    def validate_specs(self, value):
        if not isinstance(value, list) or any(not isinstance(spec, str) for spec in value):
            raise serializers.ValidationError("Specifications must be a list of text values.")
        return value

    def validate(self, attrs):
        price = attrs.get("price", getattr(self.instance, "price", None))
        compare_price = attrs.get("compare_price", getattr(self.instance, "compare_price", None))
        stock = attrs.get("stock")
        if stock is not None and self.instance and stock < self.instance.reserved:
            raise serializers.ValidationError({"stock": f"{self.instance.reserved} unit(s) are reserved for active orders."})
        if price is not None and price <= 0:
            raise serializers.ValidationError({"price": "Price must be greater than zero."})
        if compare_price is not None and price is not None and compare_price < price:
            raise serializers.ValidationError({"compare_price": "Compare price must be greater than or equal to price."})
        return attrs
