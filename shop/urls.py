from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [

    path('admin-panel/', include('shop.admin_urls')),  # Your custom admin panel
    # Django Admin
    path('django-admin/', admin.site.urls),

    # Public Pages
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Cart
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),

    # Checkout & Orders
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('invoice/<int:order_id>/', views.generate_invoice, name='generate_invoice'),
    path("cancel-order/<int:order_id>/", views.cancel_order, name="cancel_order"),
    path("return-order/<int:order_id>/", views.request_return, name="request_return"),
    path("replace-order/<int:order_id>/", views.request_replace, name="request_replace"),
    path('check-eligibility/<int:order_id>/', views.check_eligibility, name='check_eligibility'),

    path('submit-review/<int:product_id>/', views.submit_review, name='submit_review'),
    path('delete-review/<int:review_id>/', views.delete_review, name='delete_review'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('toggle-wishlist/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('remove-from-wishlist/<int:wishlist_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Authentication
    path('accounts/', include('django.contrib.auth.urls')),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # User Account
    path('account/', views.account_details, name='account'),

    # Coupons
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),

    # Contact
    path('contact/', views.contact, name='contact'),

    # Static Pages
    path('about/', views.about, name='about'),
    path('privacy-policy/', views.privacy_policy, name='privacy'),
    path('terms-of-use/', views.terms_of_use, name='terms'),
    path('sales-refunds/', views.sales_refunds, name='sales_refunds'),
    path('faq/', views.faq, name='faq'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)