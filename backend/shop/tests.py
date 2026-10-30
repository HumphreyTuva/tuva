from io import BytesIO
from datetime import datetime, timezone
import os
import tempfile
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .imagesearch import embed
from .models import ChatMessage, Order, Product, StockAlert
from . import mpesa
from .mpesa import normalize
from .tasks import branded


class StorefrontApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.product = Product.objects.create(
            name="ProBook 14",
            subtitle="14-inch business laptop",
            category="business",
            price_min="679.00",
            price_max="799.00",
            specs=["16GB RAM", "512GB SSD"],
            stock=5,
        )

    def test_product_search_filters_category_and_name(self):
        response = self.client.get("/api/products/", {"q": "probook", "category": "BUSINESS"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["ProBook 14"])

    def test_product_prices_are_kes_values(self):
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["price_min_kes"], 679)
        self.assertEqual(response.data[0]["price_max_kes"], 799)

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
        self.assertEqual(order.status, "pending")

    def test_stock_alert_subscription_and_restock_notification(self):
        with patch("shop.views.send_html.delay") as send_email:
            response = self.client.post(
                "/api/alerts/",
                {"email": "buyer@example.com", "query": "ProBook 14"},
                format="json",
            )
            duplicate = self.client.post(
                "/api/alerts/",
                {"email": "buyer@example.com", "query": "ProBook 14"},
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        send_email.assert_called_once()

        alert = StockAlert.objects.get()
        alert.product = self.product
        alert.save(update_fields=["product"])
        with patch("shop.tasks.notify_back_in_stock.delay") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                self.product.stock = 0
                self.product.save(update_fields=["stock"])
                self.product.stock = 1
                self.product.save(update_fields=["stock"])
        notify.assert_called_once_with(self.product.pk)

    def test_successful_payment_callback_verifies_amount_and_is_idempotent(self):
        user = get_user_model().objects.create_user(username="customer", email="")
        order = Order.objects.create(
            user=user,
            product=self.product,
            qty=2,
            amount="1358.00",
            payment_amount=177219,
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
                            {"Name": "Amount", "Value": 177219},
                            {"Name": "MpesaReceiptNumber", "Value": "TUVA123"},
                        ],
                    },
                },
            },
        }

        first = self.client.post("/api/mpesa/callback/", payload, format="json")
        second = self.client.post("/api/mpesa/callback/", payload, format="json")

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.receipt, "TUVA123")
        self.assertEqual(self.product.stock, 3)

    def test_mpesa_callback_rejects_mismatched_amount(self):
        user = get_user_model().objects.create_user(username="other", email="")
        order = Order.objects.create(
            user=user,
            product=self.product,
            amount="679.00",
            payment_amount=88470,
            phone="254712345678",
            checkout_request_id="mismatch-test",
        )
        self.client.post(
            "/api/mpesa/callback/",
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
        self.assertEqual(order.status, "failed")
        self.assertEqual(self.product.stock, 5)

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
        self.assertEqual(mpesa.kes_amount("679.50"), 680)
        self.assertIsNone(mpesa.kes_amount("0"))

    def test_branded_email_escapes_user_content(self):
        html = branded("<script>alert(1)</script>", "Laptop <img src=x>", "Browse", "https://example.test/?q=a&b")

        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
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
                    "price_min": "500.00",
                    "price_max": "650.00",
                    "rating": "4.5",
                    "specs": '["16GB RAM"]',
                    "stock": "12",
                    "badge": "New",
                    "image": SimpleUploadedFile("new-laptop.png", image_bytes.getvalue(), content_type="image/png"),
                },
                format="multipart",
            )
            product_id = created.data.get("id")
            edited = self.client.patch(
                f"/api/management/products/{product_id}/",
                {"name": "Updated Laptop", "price_min": "550.00", "specs": '["32GB RAM"]'},
                format="multipart",
            )
            deleted = self.client.delete(f"/api/management/products/{product_id}/delete/")

        self.assertEqual(created.status_code, 201)
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data["name"], "Updated Laptop")
        self.assertEqual(edited.data["specs"], ["32GB RAM"])
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product_id).exists())
        self.assertEqual([item["id"] for item in self.client.get("/api/products/").data], [self.product.pk])

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

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

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
