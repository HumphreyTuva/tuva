from rest_framework import serializers
from . import mpesa
from .models import Product, ProductImage


class ProductSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    price_min = serializers.DecimalField(source="price", max_digits=10, decimal_places=2, read_only=True)
    price_max = serializers.DecimalField(source="compare_price", max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    price_min_kes = serializers.SerializerMethodField()
    price_max_kes = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    image_items = serializers.SerializerMethodField()
    image_files = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True,
    )
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "subtitle", "category", "price", "compare_price", "price_min", "price_max",
            "price_min_kes", "price_max_kes", "specs", "image", "images", "image_items", "image_files",
            "stock", "in_stock", "badge", "is_active",
        ]
        extra_kwargs = {"image": {"required": False}}

    def get_in_stock(self, o): return o.available_stock > 0

    def get_images(self, o):
        image_field = self.fields["image"]
        images = [image_field.to_representation(o.image)] if o.image else []
        images.extend(
            image_field.to_representation(gallery_image.image)
            for gallery_image in o.gallery_images.all()
        )
        return images

    def get_image_items(self, o):
        image_field = self.fields["image"]
        images = []
        if o.image:
            images.append({
                "id": "primary",
                "url": image_field.to_representation(o.image),
                "primary": True,
            })
        images.extend(
            {
                "id": gallery_image.pk,
                "url": image_field.to_representation(gallery_image.image),
                "primary": False,
            }
            for gallery_image in o.gallery_images.all()
        )
        return images

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
        if self.instance is None and not attrs.get("image") and not attrs.get("image_files"):
            raise serializers.ValidationError({"image_files": "Upload at least one product image."})
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

    def create(self, validated_data):
        image_files = validated_data.pop("image_files", [])
        if not validated_data.get("image") and image_files:
            validated_data["image"] = image_files.pop(0)
        product = super().create(validated_data)
        for image in image_files:
            ProductImage.objects.create(product=product, image=image)
        return product

    def update(self, instance, validated_data):
        image_files = validated_data.pop("image_files", [])
        product = super().update(instance, validated_data)
        for image in image_files:
            ProductImage.objects.create(product=product, image=image)
        return product
