from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),

    path('checkout/', views.checkout, name='checkout'),
    path('contact/', views.contact, name='contact'),


    path('accounts/', include('django.contrib.auth.urls')),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('about/', views.about, name='about'),
    path('privacy-policy/', views.privacy_policy, name='privacy'),
    path('terms-of-use/', views.terms_of_use, name='terms'),
    path('sales-refunds/', views.sales_refunds, name='sales_refunds'),
    path('faq/', views.faq, name='faq'),

    path('account/', views.account_details, name='account'),
    path('orders/', views.order_history, name='order_history'),
    path('wishlist/', views.wishlist, name='wishlist'),

     path('invoice/<int:order_id>/', views.generate_invoice, name='generate_invoice'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('order-success/', views.order_success, name='order_success'),
]