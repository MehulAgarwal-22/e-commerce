from django.urls import path
from . import admin_views

urlpatterns = [
    # Auth
    path('login/', admin_views.admin_login, name='admin_login'),
    path('logout/', admin_views.admin_logout, name='admin_logout'),
    
    # Dashboard
    path('', admin_views.admin_dashboard, name='admin_dashboard'),
    
    # Products
    path('products/', admin_views.admin_products, name='admin_products'),
    path('products/add/', admin_views.admin_add_product, name='admin_add_product'),
    path('products/edit/<int:product_id>/', admin_views.admin_edit_product, name='admin_edit_product'),
    path('products/delete/<int:product_id>/', admin_views.admin_delete_product, name='admin_delete_product'),
    path('products/bulk-stock-update/', admin_views.admin_bulk_stock_update, name='admin_bulk_stock_update'),
    
    # Categories
    path('categories/', admin_views.admin_categories, name='admin_categories'),
    path('categories/add/', admin_views.admin_add_category, name='admin_add_category'),
    path('categories/edit/<int:category_id>/', admin_views.admin_edit_category, name='admin_edit_category'),
    path('categories/delete/<int:category_id>/', admin_views.admin_delete_category, name='admin_delete_category'),
    
    # Orders
    path('orders/', admin_views.admin_orders, name='admin_orders'),
    path('orders/<int:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    
    # Customers
    path('customers/', admin_views.admin_customers, name='admin_customers'),
    path('customers/<int:customer_id>/', admin_views.admin_customer_detail, name='admin_customer_detail'),
    
    # Coupons
    path('coupons/', admin_views.admin_coupons, name='admin_coupons'),
    path('coupons/add/', admin_views.admin_add_coupon, name='admin_add_coupon'),
    path('coupons/edit/<int:coupon_id>/', admin_views.admin_edit_coupon, name='admin_edit_coupon'),
    path('coupons/delete/<int:coupon_id>/', admin_views.admin_delete_coupon, name='admin_delete_coupon'),
    
    # Payments
    path('payments/', admin_views.admin_payments, name='admin_payments'),
    
    # Settings
    path('settings/', admin_views.admin_settings, name='admin_settings'),
    
    path('profile/', admin_views.admin_profile, name='admin_profile'),
    path('profile/update/', admin_views.admin_profile_update, name='admin_profile_update'),
    path('profile/change-password/', admin_views.admin_change_password, name='admin_change_password'),
    path('profile/upload-picture/', admin_views.admin_upload_picture, name='admin_upload_picture'),

    path('returns/', admin_views.admin_returns, name='admin_returns'),
    path('returns/<int:return_id>/', admin_views.admin_return_detail, name='admin_return_detail'),
    path('returns/bulk-approve/', admin_views.admin_bulk_approve_returns, name='admin_bulk_approve_returns'),
    path('replacements/', admin_views.admin_replacements, name='admin_replacements'),
    path('replacements/<int:replace_id>/', admin_views.admin_replacement_detail, name='admin_replacement_detail'),
]