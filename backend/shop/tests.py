from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
import os
import tempfile
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone as django_timezone
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .imagesearch import embed
from .models import ChatMessage, DeliveryZone, DiscountCode, MpesaPayment, Order, Product, ProductImage, StockAlert, StockMovement
from . import mpesa
from .mpesa import normalize
from .tasks import branded


@override_settings(SECURE_SSL_REDIRECT=False)
class StorefrontApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.product = Product.objects.create(
            name="ProBook 14",
            subtitle="14-inch business laptop",
            category="business",
            price="679.00",
            compare_price="799.00",
            specs=["16GB RAM", "512GB SSD"],
            stock=5,
        )

    def test_product_search_filters_category_and_name(self):
        response = self.client.get("/api/products/", {"q": "probook", "category": "BUSINESS"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["ProBook 14"])

    def test_products_support_offset_pagination(self):
        second_product = Product.objects.create(
            name="TravelMate 14",
            subtitle="Business laptop",
            category="business",
            price="500.00",
            stock=2,
        )

        first_page = self.client.get("/api/products/", {"offset": 0})
        next_page = self.client.get("/api/products/", {"offset": 1})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual([item["id"] for item in first_page.data], [self.product.pk, second_product.pk])
        self.assertEqual([item["id"] for item in next_page.data], [second_product.pk])
        self.assertEqual(self.client.get("/api/products/", {"offset": -1}).status_code, 400)
        self.assertEqual(self.client.get("/api/products/", {"offset": "invalid"}).status_code, 400)

    def test_product_count_reports_all_active_filtered_results(self):
        second_product = Product.objects.create(
            name="TravelMate 14",
            subtitle="Business laptop",
            category="business",
            price="500.00",
            stock=2,
        )
        Product.objects.create(
            name="Gaming laptop",
            subtitle="Gaming laptop",
            category="gaming",
            price="800.00",
            stock=2,
        )

        response = self.client.get("/api/products/", {"category": "business", "include_count": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.product.pk, second_product.pk])

    def test_product_detail_returns_product_and_hides_archived_products(self):
        response = self.client.get(f"/api/products/{self.product.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "ProBook 14")
        self.assertEqual(response.data["specs"], ["16GB RAM", "512GB SSD"])

        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(f"/api/products/{self.product.pk}/").status_code, 404)

    def test_product_prices_are_kes_values(self):
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["price_min_kes"], 679)
        self.assertEqual(response.data[0]["price_max_kes"], 799)
        self.assertNotIn("rating", response.data[0])

    def test_product_stock_updates_are_reflected_without_waiting_for_cache(self):
        first = self.client.get("/api/products/")
        self.assertEqual(first.data[0]["stock"], 5)

        self.product.stock = 0
        self.product.save(update_fields=["stock"])

        updated = self.client.get("/api/products/")
        self.assertEqual(updated.data[0]["stock"], 0)

    def test_image_search_returns_visual_matches(self):
        image_bytes = BytesIO()
        Image.new("RGB", (32, 32), color=(32, 92, 156)).save(image_bytes, format="PNG")
        self.product.embedding = embed(BytesIO(image_bytes.getvalue()))
        self.product.save(update_fields=["embedding"])

        upload = SimpleUploadedFile("laptop.png", image_bytes.getvalue(), content_type="image/png")
        response = self.client.post("/api/image-search/", {"image": upload}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [self.product.pk])

    def test_checkout_quote_uses_kes_price_with_rounding(self):
        response = self.client.get("/api/checkout/quote/", {"product": self.product.pk, "qty": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["amount_kes"], 1358)

    def test_checkout_quote_checks_available_quantity_without_a_rate(self):
        unavailable = self.client.get("/api/checkout/quote/", {"product": self.product.pk, "qty": 6})
        self.assertEqual(unavailable.status_code, 400)

    def test_server_cart_quote_recalculates_lines_and_ignores_discount_codes(self):
        second = Product.objects.create(name="ThinkPad X", category="business", price="300.00", stock=3)
        zone = DeliveryZone.objects.create(name="Nairobi", fee="250.00")
        response = self.client.post("/api/checkout/quote/", {
            "items": [{"product": self.product.pk, "quantity": 2}, {"product": second.pk, "quantity": 1}],
            "delivery_zone": zone.pk,
            "discount_code": "tuva10",
            "total": "1",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subtotal"], Decimal("1658.00"))
        self.assertEqual(response.data["delivery_fee"], Decimal("250.00"))
        self.assertNotIn("discount", response.data)
        self.assertEqual(response.data["total"], Decimal("1908.00"))
        self.assertEqual(response.data["amount_kes"], 1908)

    def test_multi_item_checkout_reserves_each_line_and_ignores_browser_total(self):
        second = Product.objects.create(name="ThinkPad X", category="business", price="300.00", stock=3)
        user = get_user_model().objects.create_user(username="multi-payer")
        self.client.force_authenticate(user=user)
        with patch("shop.views.mpesa.stk_push", return_value={"ResponseCode": "0", "CheckoutRequestID": "multi-checkout"}) as push:
            response = self.client.post("/api/checkout/", {
                "items": [{"product": self.product.pk, "quantity": 2}, {"product": second.pk, "quantity": 1}],
                "phone": "0712345678", "total": "1",
            }, format="json")
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.data["order"])
        self.assertEqual(order.total, Decimal("1658.00"))
        self.assertEqual(order.items.count(), 2)
        self.product.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.product.reserved, 2)
        self.assertEqual(second.reserved, 1)
        push.assert_called_once_with("254712345678", 1658, f"TUVA{order.pk}")

    def test_live_chat_persists_customer_message_for_conversation(self):
        conversation = str(uuid4())
        response = self.client.post(
            "/api/chat/",
            {"conversation": conversation, "message": "Do you have this in stock?"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(ChatMessage.objects.get().conversation), conversation)
        history = self.client.get("/api/chat/", {"conversation": conversation})
        self.assertEqual(history.data["messages"][0]["message"], "Do you have this in stock?")

    def test_live_chat_rejects_malformed_conversation_and_oversized_message(self):
        invalid_id = self.client.get("/api/chat/", {"conversation": "not-a-uuid"})
        self.assertEqual(invalid_id.status_code, 400)

        response = self.client.post(
            "/api/chat/",
            {"conversation": str(uuid4()), "message": "x" * 2001},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_checkout_requires_authenticated_user(self):
        response = self.client.post(
            "/api/checkout/",
            {"product": self.product.pk, "phone": "0712345678", "qty": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(ALLOW_GUEST_CHECKOUT=True)
    def test_guest_checkout_returns_private_access_token(self):
        with patch("shop.views.mpesa.stk_push", return_value={"ResponseCode": "0", "CheckoutRequestID": "guest-checkout"}):
            response = self.client.post("/api/checkout/", {
                "product": self.product.pk, "phone": "0712345678", "full_name": "Guest Buyer",
                "email": "guest@example.com", "qty": 1,
            }, format="json", HTTP_IDEMPOTENCY_KEY="guest-checkout-123")
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.data["order"])
        self.assertIsNone(order.user)
        self.assertEqual(order.email, "guest@example.com")
        self.assertEqual(len(response.data["access_token"]), 48)
        self.assertEqual(self.client.get(f"/api/orders/{order.pk}/").status_code, 404)
        status = self.client.get(f"/api/orders/{order.pk}/", HTTP_X_ORDER_ACCESS_TOKEN=response.data["access_token"])
        self.assertEqual(status.status_code, 200)

    @override_settings(DEBUG=True, MPESA_SIMULATE=True)
    def test_simulated_mpesa_completes_once_after_six_seconds(self):
        user = get_user_model().objects.create_user(username="simulation-payer")
        self.client.force_authenticate(user=user)
        with patch("shop.views.mpesa.stk_push") as stk_push:
            response = self.client.post("/api/checkout/", {"product": self.product.pk, "phone": "0712345678"}, format="json")
            order = Order.objects.get(pk=response.data["order"])
            order.created = django_timezone.now() - timedelta(seconds=7)
            order.save(update_fields=["created"])
            first_status = self.client.get(f"/api/orders/{order.pk}/")
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, 4)
            second_status = self.client.get(f"/api/orders/{order.pk}/")
        stk_push.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(first_status.data["payment_status"], "successful")
        self.assertEqual(second_status.data["payment_status"], "successful")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)

    def test_authenticated_checkout_sends_kes_amount_to_daraja(self):
        user = get_user_model().objects.create_user(username="payer")
        self.client.force_authenticate(user=user)
        with patch(
            "shop.views.mpesa.stk_push",
            return_value={"ResponseCode": "0", "CheckoutRequestID": "daraja-checkout"},
        ) as stk_push:
            response = self.client.post(
                "/api/checkout/",
                {"product": self.product.pk, "phone": "0712345678", "qty": 2},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["amount_kes"], 1358)
        stk_push.assert_called_once_with("254712345678", 1358, f"TUVA{response.data['order']}")
        order = Order.objects.get(pk=response.data["order"])
        self.assertEqual(order.amount, 1358)
        self.assertEqual(order.payment_amount, 1358)
        self.assertEqual(order.status, "pending_payment")
        self.assertEqual(order.payment_status, "pending")
        self.assertTrue(order.stock_reserved)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved, 2)
        self.assertEqual(order.items.count(), 1)

    def test_checkout_idempotency_key_does_not_create_duplicate_orders(self):
        user = get_user_model().objects.create_user(username="idempotent-payer")
        self.client.force_authenticate(user=user)
        headers = {"HTTP_IDEMPOTENCY_KEY": "checkout-request-123"}
        with patch("shop.views.mpesa.stk_push", return_value={"ResponseCode": "0", "CheckoutRequestID": "idempotent-daraja"}) as stk_push:
            first = self.client.post("/api/checkout/", {"product": self.product.pk, "phone": "0712345678", "qty": 1}, format="json", **headers)
            second = self.client.post("/api/checkout/", {"product": self.product.pk, "phone": "0712345678", "qty": 1}, format="json", **headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["order"], second.data["order"])
        self.assertEqual(Order.objects.filter(user=user).count(), 1)
        stk_push.assert_called_once()

    def test_expire_orders_queries_daraja_then_releases_cancelled_reservation(self):
        user = get_user_model().objects.create_user(username="expiring-payer")
        order = Order.objects.create(user=user, product=self.product, amount="679.00", payment_amount=679,
                                     phone="254712345678", checkout_request_id="expiry-checkout", stock_reserved=True)
        order.created = django_timezone.now() - timedelta(minutes=21)
        order.save(update_fields=["created"])
        self.product.reserved = 1
        self.product.save(update_fields=["reserved"])
        with patch("shop.management.commands.expire_orders.mpesa.query", return_value={"ResultCode": 1032, "ResultDesc": "Cancelled"}) as query:
            call_command("expire_orders", stdout=StringIO())
        query.assert_called_once_with("expiry-checkout")
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.payment_status, "cancelled")
        self.assertFalse(order.stock_reserved)
        self.assertEqual(self.product.reserved, 0)

    def test_order_status_rate_limits_daraja_query_in_shared_database(self):
        user = get_user_model().objects.create_user(username="polling-payer")
        order = Order.objects.create(user=user, product=self.product, amount="679.00", payment_amount=679,
                                     phone="254712345678", checkout_request_id="polling-checkout")
        order.created = django_timezone.now() - timedelta(seconds=30)
        order.save(update_fields=["created"])
        self.client.force_authenticate(user=user)
        with patch("shop.views.mpesa.query", return_value={}) as query:
            self.client.get(f"/api/orders/{order.pk}/")
            self.client.get(f"/api/orders/{order.pk}/")
        query.assert_called_once_with("polling-checkout")
        order.refresh_from_db()
        self.assertIsNotNone(order.last_status_query_at)

    def test_stock_alert_subscription_and_restock_notification(self):
        with patch("shop.views.send_html.delay") as send_email:
            response = self.client.post(
                "/api/alerts/",
                {"email": "buyer@example.com", "query": "ProBook 14", "consent": True},
                format="json",
            )
            duplicate = self.client.post(
                "/api/alerts/",
                {"email": "buyer@example.com", "query": "ProBook 14", "consent": True},
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        send_email.assert_called_once()

        from .models import AvailabilityRequest
        alert = AvailabilityRequest.objects.get()
        alert.query = self.product.model or self.product.name
        alert.matched_product = self.product
        alert.save(update_fields=["query", "matched_product"])
        with patch("shop.tasks.notify_availability_request") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                self.product.stock = 0
                self.product.save(update_fields=["stock"])
                self.product.stock = 1
                self.product.save(update_fields=["stock"])
        notify.assert_called_once()

    @override_settings(MPESA_CALLBACK_SECRET="test-secret")
    def test_successful_payment_callback_verifies_amount_and_is_idempotent(self):
        user = get_user_model().objects.create_user(username="customer", email="")
        order = Order.objects.create(
            user=user,
            product=self.product,
            qty=2,
            amount="1358.00",
            payment_amount=1358,
            phone="254712345678",
            checkout_request_id="checkout-test",
        )
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "checkout-test",
                    "ResultCode": 0,
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1358},
                            {"Name": "MpesaReceiptNumber", "Value": "TUVA123"},
                        ],
                    },
                },
            },
        }

        first = self.client.post("/api/mpesa/callback/test-secret/", payload, format="json")
        second = self.client.post("/api/mpesa/callback/test-secret/", payload, format="json")

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(order.status, "processing")
        self.assertEqual(order.payment_status, "successful")
        self.assertEqual(order.receipt, "TUVA123")
        self.assertEqual(self.product.stock, 3)

    @override_settings(MPESA_CALLBACK_SECRET="test-secret")
    def test_mpesa_callback_rejects_mismatched_amount(self):
        user = get_user_model().objects.create_user(username="other", email="")
        order = Order.objects.create(
            user=user,
            product=self.product,
            amount="679.00",
            payment_amount=679,
            phone="254712345678",
            checkout_request_id="mismatch-test",
        )
        self.client.post(
            "/api/mpesa/callback/test-secret/",
            {
                "Body": {
                    "stkCallback": {
                        "CheckoutRequestID": "mismatch-test",
                        "ResultCode": 0,
                        "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 1}]},
                    },
                },
            },
            format="json",
        )

        order.refresh_from_db()
        self.assertEqual(order.status, "pending_payment")
        self.assertEqual(order.payment_status, "reconcile")
        self.assertEqual(self.product.stock, 5)

    @override_settings(MPESA_CALLBACK_SECRET="test-secret")
    def test_late_payment_after_cancelled_order_goes_to_reconciliation(self):
        user = get_user_model().objects.create_user(username="late-payer")
        order = Order.objects.create(user=user, product=self.product, amount="679.00", payment_amount=679,
                                     phone="254712345678", checkout_request_id="late-checkout",
                                     status="cancelled", payment_status="cancelled")
        response = self.client.post("/api/mpesa/callback/test-secret/", {
            "Body": {"stkCallback": {"CheckoutRequestID": "late-checkout", "ResultCode": 0,
                "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 679}, {"Name": "MpesaReceiptNumber", "Value": "LATE123"}]}}},
        }, format="json")
        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.payment_status, "reconcile")
        self.assertEqual(self.product.stock, 5)

    @override_settings(MPESA_CALLBACK_SECRET="test-secret")
    def test_duplicate_mpesa_receipt_is_reconciled_without_second_stock_debit(self):
        prior_user = get_user_model().objects.create_user(username="receipt-owner")
        prior_order = Order.objects.create(user=prior_user, product=self.product, amount="679.00", payment_amount=679,
                                           phone="254712345678", checkout_request_id="receipt-owner-checkout",
                                           status="processing", payment_status="successful", stock_committed=True, receipt="SHARED1")
        MpesaPayment.objects.create(order=prior_order, phone=prior_order.phone, amount=679,
                                    checkout_request_id="receipt-owner-checkout", status="successful", receipt="SHARED1")
        user = get_user_model().objects.create_user(username="receipt-duplicate")
        order = Order.objects.create(user=user, product=self.product, amount="679.00", payment_amount=679,
                                     phone="254712345678", checkout_request_id="receipt-duplicate-checkout")
        self.client.post("/api/mpesa/callback/test-secret/", {
            "Body": {"stkCallback": {"CheckoutRequestID": "receipt-duplicate-checkout", "ResultCode": 0,
                "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 679}, {"Name": "MpesaReceiptNumber", "Value": "SHARED1"}]}}},
        }, format="json")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, "reconcile")
        self.assertEqual(self.product.stock, 5)

    def test_mpesa_callback_rejects_wrong_secret(self):
        response = self.client.post("/api/mpesa/callback/wrong-secret/", {}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_phone_normalization_accepts_common_kenyan_formats(self):
        self.assertEqual(normalize("0712 345 678"), "254712345678")
        self.assertEqual(normalize("+254 712 345 678"), "254712345678")

    def test_daraja_access_token_uses_client_credentials_and_is_cached(self):
        cache.clear()
        with patch.dict(os.environ, {
            "MPESA_ENV": "sandbox",
            "MPESA_CONSUMER_KEY": "test-key",
            "MPESA_CONSUMER_SECRET": "test-secret",
        }), patch("shop.mpesa.requests.get") as get:
            get.return_value.json.return_value = {"access_token": "test-token", "expires_in": "3600"}

            self.assertEqual(mpesa._token(), "test-token")
            self.assertEqual(mpesa._token(), "test-token")

        get.assert_called_once_with(
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            auth=("test-key", "test-secret"),
            timeout=15,
        )

    def test_stk_push_uses_bearer_token_and_east_africa_timestamp(self):
        fixed_now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        with patch.dict(os.environ, {
            "MPESA_ENV": "sandbox",
            "MPESA_SHORTCODE": "123456",
            "MPESA_TILL": "654321",
            "MPESA_PASSKEY": "test-passkey",
            "MPESA_CALLBACK_URL": "https://example.test/api/mpesa/callback/",
            "MPESA_CALLBACK_SECRET": "",
        }), patch("shop.mpesa._token", return_value="test-token"), patch(
            "shop.mpesa.requests.post"
        ) as post, patch("shop.mpesa.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            post.return_value.json.return_value = {"ResponseCode": "0"}

            mpesa.stk_push("0712 345 678", 500, "TUVA1")

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer test-token"})
        self.assertEqual(kwargs["json"]["Timestamp"], "20260101030000")
        self.assertEqual(kwargs["json"]["Password"], "MTIzNDU2dGVzdC1wYXNza2V5MjAyNjAxMDEwMzAwMDA=")
        self.assertEqual(kwargs["json"]["PartyA"], "254712345678")
        self.assertEqual(kwargs["json"]["PartyB"], "654321")
        self.assertEqual(kwargs["json"]["Amount"], 500)

    def test_stk_query_uses_daraja_bearer_token(self):
        fixed_now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        with patch.dict(os.environ, {
            "MPESA_ENV": "sandbox",
            "MPESA_SHORTCODE": "123456",
            "MPESA_PASSKEY": "test-passkey",
        }), patch("shop.mpesa._token", return_value="test-token"), patch(
            "shop.mpesa.requests.post"
        ) as post, patch("shop.mpesa.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            post.return_value.json.return_value = {"ResponseCode": "0"}

            mpesa.query("checkout-id")

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query")
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer test-token"})
        self.assertEqual(kwargs["json"]["CheckoutRequestID"], "checkout-id")

    def test_mpesa_amount_uses_price_as_kes(self):
        self.assertEqual(mpesa.round_kes_amount("679.50"), 680)
        self.assertIsNone(mpesa.round_kes_amount("0"))

    def test_branded_email_escapes_user_content(self):
        html = branded("<script>alert(1)</script>", "Laptop <img src=x>", "Browse", "https://example.test/?q=a&b")

        self.assertNotIn("<script>", html)
        self.assertIn('<img src="https://', html)
        self.assertNotIn('<img src=x>', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp;", html)

    def test_management_dashboard_requires_staff_authentication(self):
        anonymous = self.client.get("/api/management/dashboard/")
        customer = get_user_model().objects.create_user(username="customer")
        self.client.force_authenticate(user=customer)
        regular_user = self.client.get("/api/management/dashboard/")

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(regular_user.status_code, 403)

    def test_staff_login_issues_token_but_customer_login_is_rejected(self):
        staff = get_user_model().objects.create_user(username="manager", password="secure-pass", is_staff=True)
        get_user_model().objects.create_user(username="buyer", password="secure-pass")

        staff_response = self.client.post(
            "/api/management/login/",
            {"username": "manager", "password": "secure-pass"},
            format="json",
        )
        customer_response = self.client.post(
            "/api/management/login/",
            {"username": "buyer", "password": "secure-pass"},
            format="json",
        )

        self.assertEqual(staff_response.status_code, 200)
        self.assertTrue(staff_response.data["token"])
        self.assertEqual(staff_response.data["name"], staff.username)
        self.assertEqual(customer_response.status_code, 401)

    def test_staff_can_update_stock_and_view_store_overview(self):
        staff = get_user_model().objects.create_user(username="manager", is_staff=True)
        self.client.force_authenticate(user=staff)
        cached_catalog = self.client.get("/api/products/")
        self.assertEqual(cached_catalog.data[0]["stock"], 5)

        update = self.client.patch(
            f"/api/management/products/{self.product.pk}/stock/",
            {"stock": 0},
            format="json",
        )
        dashboard = self.client.get("/api/management/dashboard/")

        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data["stock"], 0)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["metrics"]["products"], 1)
        self.assertEqual(dashboard.data["metrics"]["in_stock"], 0)
        self.assertEqual(self.client.get("/api/products/").data[0]["stock"], 0)
        movement = StockMovement.objects.filter(product=self.product).latest("created")
        self.assertEqual(movement.quantity_delta, -5)
        self.assertEqual(movement.reason, "adjustment")

    def test_staff_can_create_edit_and_delete_products(self):
        staff = get_user_model().objects.create_user(username="manager", is_staff=True)
        self.client.force_authenticate(user=staff)
        image_bytes = BytesIO()
        Image.new("RGB", (16, 16), color=(32, 92, 156)).save(image_bytes, format="PNG")

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root), patch(
            "shop.imagesearch.embed", return_value=[0.1],
        ):
            created = self.client.post(
                "/api/management/products/",
                {
                    "name": "New Laptop",
                    "subtitle": "A useful laptop",
                    "category": "business",
                    "price": "500.00",
                    "compare_price": "650.00",
                    "specs": '["16GB RAM"]',
                    "stock": "12",
                    "badge": "New",
                    "image_files": [
                        SimpleUploadedFile("new-laptop.png", image_bytes.getvalue(), content_type="image/png"),
                        SimpleUploadedFile("new-laptop-side.png", image_bytes.getvalue(), content_type="image/png"),
                    ],
                },
                format="multipart",
            )
            product_id = created.data.get("id")
            edited = self.client.patch(
                f"/api/management/products/{product_id}/",
                {
                    "name": "Updated Laptop",
                    "price": "550.00",
                    "specs": '["32GB RAM"]',
                    "image_files": [
                        SimpleUploadedFile("new-laptop-back.png", image_bytes.getvalue(), content_type="image/png"),
                    ],
                },
                format="multipart",
            )
            deleted = self.client.delete(f"/api/management/products/{product_id}/delete/")

        self.assertEqual(created.status_code, 201)
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data["name"], "Updated Laptop")
        self.assertEqual(edited.data["specs"], ["32GB RAM"])
        self.assertEqual(len(created.data["images"]), 2)
        self.assertEqual(len(edited.data["images"]), 3)
        self.assertEqual(ProductImage.objects.filter(product_id=product_id).count(), 2)
        self.assertEqual(deleted.status_code, 204)
        self.assertTrue(Product.objects.filter(pk=product_id, is_active=False).exists())
        self.assertNotIn(product_id, [item["id"] for item in self.client.get("/api/management/dashboard/").data["products"]])
        self.assertNotIn(product_id, [
            item["id"]
            for item in self.client.get("/api/management/products/", {"q": "Updated Laptop"}).data["results"]
        ])
        self.assertEqual([item["id"] for item in self.client.get("/api/products/").data], [self.product.pk])

    def test_staff_can_search_and_page_through_all_inventory_products(self):
        self.assertEqual(self.client.get("/api/management/products/", {"q": "Search target"}).status_code, 401)
        staff = get_user_model().objects.create_user(username="inventory-search-manager", is_staff=True)
        self.client.force_authenticate(user=staff)
        Product.objects.bulk_create([
            Product(
                name=f"Search target {index:02}",
                category="business",
                price="500.00",
                stock=1,
            )
            for index in range(51)
        ])

        first_page = self.client.get("/api/management/products/", {"q": "Search target"})
        second_page = self.client.get("/api/management/products/", {"q": "Search target", "offset": 50})
        missing = self.client.get("/api/management/products/", {"q": "No such product"})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data["count"], 51)
        self.assertEqual(len(first_page.data["results"]), 50)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertEqual(missing.data["count"], 0)
        self.assertEqual(missing.data["results"], [])

        inactive_product = Product.objects.create(
            name="Inactive Search target",
            category="business",
            price="500.00",
            stock=1,
            is_active=False,
        )
        filtered = self.client.get("/api/management/products/", {"q": "Search target"})
        self.assertFalse(any(item["id"] == inactive_product.pk for item in filtered.data["results"]))
        self.assertEqual(filtered.data["count"], 51)

    def test_staff_can_replace_and_delete_individual_product_images(self):
        staff = get_user_model().objects.create_user(username="image-manager", is_staff=True)
        self.client.force_authenticate(user=staff)
        image_bytes = BytesIO()
        Image.new("RGB", (16, 16), color=(32, 92, 156)).save(image_bytes, format="PNG")

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root), patch(
            "shop.imagesearch.embed", return_value=[0.1],
        ):
            created = self.client.post(
                "/api/management/products/",
                {
                    "name": "Image editor laptop",
                    "category": "business",
                    "price": "500.00",
                    "image_files": [
                        SimpleUploadedFile("main.png", image_bytes.getvalue(), content_type="image/png"),
                        SimpleUploadedFile("side.png", image_bytes.getvalue(), content_type="image/png"),
                        SimpleUploadedFile("back.png", image_bytes.getvalue(), content_type="image/png"),
                    ],
                },
                format="multipart",
            )
            product_id = created.data["id"]
            original_gallery_id = created.data["image_items"][1]["id"]
            replacement = self.client.patch(
                f"/api/management/products/{product_id}/images/{original_gallery_id}/",
                {"image": SimpleUploadedFile("replacement.png", image_bytes.getvalue(), content_type="image/png")},
                format="multipart",
            )
            remaining_gallery_id = replacement.data["image_items"][2]["id"]
            deleted_gallery = self.client.delete(
                f"/api/management/products/{product_id}/images/{remaining_gallery_id}/",
            )
            deleted_primary = self.client.delete(
                f"/api/management/products/{product_id}/images/primary/",
            )
            rejected_last_image = self.client.delete(
                f"/api/management/products/{product_id}/images/primary/",
            )

        self.assertEqual(created.status_code, 201)
        self.assertEqual([item["id"] for item in created.data["image_items"]][0], "primary")
        self.assertEqual(replacement.status_code, 200)
        self.assertEqual(len(replacement.data["images"]), 3)
        self.assertEqual(deleted_gallery.status_code, 200)
        self.assertEqual(deleted_primary.status_code, 200)
        self.assertEqual(deleted_primary.data["image_items"][0]["id"], "primary")
        self.assertEqual(len(deleted_primary.data["images"]), 1)
        self.assertEqual(rejected_last_image.status_code, 400)
        self.assertEqual(ProductImage.objects.filter(product_id=product_id).count(), 0)

    def test_product_management_requires_staff_and_preserves_ordered_products(self):
        self.assertEqual(self.client.post("/api/management/products/", {}, format="json").status_code, 401)
        customer = get_user_model().objects.create_user(username="customer")
        self.client.force_authenticate(user=customer)
        self.assertEqual(self.client.delete(f"/api/management/products/{self.product.pk}/delete/").status_code, 403)

        staff = get_user_model().objects.create_user(username="manager", is_staff=True)
        self.client.force_authenticate(user=staff)
        buyer = get_user_model().objects.create_user(username="buyer")
        Order.objects.create(user=buyer, product=self.product, amount="679.00", phone="254712345678")
        response = self.client.delete(f"/api/management/products/{self.product.pk}/delete/")

        self.assertEqual(response.status_code, 204)
        self.assertTrue(Product.objects.filter(pk=self.product.pk, is_active=False).exists())

    def test_authenticated_user_can_sign_out_and_revoke_token(self):
        user = get_user_model().objects.create_user(username="buyer")
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post("/api/auth/logout/")
        dashboard = self.client.get("/api/management/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
        self.assertEqual(dashboard.status_code, 401)

    def test_staff_can_read_and_reply_to_support_conversations(self):
        staff = get_user_model().objects.create_user(username="manager", is_staff=True)
        conversation = uuid4()
        ChatMessage.objects.create(conversation=conversation, message="Can you help me choose?")
        self.client.force_authenticate(user=staff)

        history = self.client.get(f"/api/management/conversations/{conversation}/")
        reply = self.client.post(
            f"/api/management/conversations/{conversation}/reply/",
            {"message": "Of course, what is your budget?"},
            format="json",
        )

        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["messages"][0]["message"], "Can you help me choose?")
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(reply.data["sender"], "support")
        self.assertEqual(ChatMessage.objects.filter(conversation=conversation).count(), 2)
