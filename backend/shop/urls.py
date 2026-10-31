from django.urls import path
from . import views as v
from . import management_views as management
urlpatterns = [path("products/", v.products), path("image-search/", v.image_search), path("alerts/", v.subscribe_alert),
 path("store-config/", v.store_config), path("delivery-zones/", v.delivery_zones),
 path("auth/google/", v.google_login), path("auth/register/", v.account_register), path("auth/login/", v.account_login), path("auth/logout/", v.logout), path("checkout/", v.checkout), path("checkout/quote/", v.checkout_quote),
 path("orders/<int:pk>/", v.order_status), path("mpesa/callback/<str:secret>/", v.mpesa_callback),
 path("assistant/", v.assistant), path("chat/", v.live_chat),
 path("management/login/", management.admin_login), path("management/dashboard/", management.admin_dashboard),
 path("management/products/<int:pk>/stock/", management.admin_update_stock),
 path("management/products/", management.admin_create_product),
 path("management/products/<int:pk>/", management.admin_update_product),
 path("management/products/<int:pk>/delete/", management.admin_delete_product),
 path("management/conversations/<uuid:conversation>/", management.admin_conversation),
 path("management/conversations/<uuid:conversation>/reply/", management.admin_reply)]
