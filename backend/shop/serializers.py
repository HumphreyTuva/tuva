from rest_framework import serializers
from . import mpesa
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField()
    price = serializers.DecimalField(source="price_min", max_digits=10, decimal_places=2, required=False)
    price_min_kes = serializers.SerializerMethodField()
    price_max_kes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "subtitle", "category", "price", "price_min", "price_max",
            "price_min_kes", "price_max_kes", "rating", "specs", "image",
            "stock", "in_stock", "badge",
        ]

    def get_in_stock(self, o): return o.stock > 0

    def get_price_min_kes(self, o):
        return mpesa.kes_amount(o.price_min)

    def get_price_max_kes(self, o):
        return mpesa.kes_amount(o.price_max)

    def validate_stock(self, value):
        if value > 1_000_000:
            raise serializers.ValidationError("Stock must be between 0 and 1,000,000.")
        return value

    def validate_rating(self, value):
        if not 0 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 0 and 5.")
        return value

    def validate_specs(self, value):
        if not isinstance(value, list) or any(not isinstance(spec, str) for spec in value):
            raise serializers.ValidationError("Specifications must be a list of text values.")
        return value

    def validate(self, attrs):
        price = attrs.get("price")
        if price is not None:
            attrs.setdefault("price_min", price)
            attrs.setdefault("price_max", price)
        price_min = attrs.get("price_min", getattr(self.instance, "price_min", None))
        price_max = attrs.get("price_max", getattr(self.instance, "price_max", None))
        if price_min is not None and price_max is not None and price_min > price_max:
            raise serializers.ValidationError({"price_max": "Maximum price must be greater than or equal to minimum price."})
        return attrs
