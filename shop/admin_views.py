from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import csv
from django.http import HttpResponse
from .models import *

# ===============================
# ADMIN DECORATOR
# ===============================
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Admin required.')
        return redirect('home')
    return wrapper

# ===============================
# ADMIN LOGIN
# ===============================
def admin_login(request):
    # If user is already logged in and is superuser, redirect to dashboard
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Access denied. Admin privileges required.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin/test_login.html')

def admin_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('admin_login')

# ===============================
# ADMIN DASHBOARD
# ===============================
@admin_required
def admin_dashboard(request):
    today = timezone.now().date()
    
    # Orders
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    processing_orders = Order.objects.filter(status='Processing').count()
    shipped_orders = Order.objects.filter(status='Shipped').count()
    delivered_orders = Order.objects.filter(status='Delivered').count()
    cancelled_orders = Order.objects.filter(status='Cancelled').count()
    
    # Today's orders
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = Order.objects.filter(
        created_at__date=today, 
        status='Delivered'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Revenue
    total_revenue = Order.objects.filter(
        status='Delivered'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Products
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(
        stock__gt=0, 
        stock__lte=F('low_stock_threshold')
    ).count()
    out_of_stock_products = Product.objects.filter(stock=0).count()
    in_stock_products = total_products - low_stock_products - out_of_stock_products
    
    # Users
    total_customers = User.objects.filter(is_superuser=False).count()
    new_customers_today = User.objects.filter(
        date_joined__date=today,
        is_superuser=False
    ).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    # Recent products
    recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
    
    # Chart data for last 7 days
    last_7_days = []
    daily_revenue = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        last_7_days.append(day.strftime('%a'))
        revenue = Order.objects.filter(
            created_at__date=day,
            status='Delivered'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        daily_revenue.append(float(revenue))

    # Return/Replace stats
    pending_returns = ReturnRequest.objects.filter(status='pending').count()
    pending_replacements = ReplaceRequest.objects.filter(status='pending').count()
    
    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'in_stock_products': in_stock_products,
        'total_customers': total_customers,
        'new_customers_today': new_customers_today,
        'recent_orders': recent_orders,
        'recent_products': recent_products,
        'chart_labels': last_7_days,
        'chart_data': daily_revenue,
        'pending_returns': pending_returns,
        'pending_replacements': pending_replacements,
    }
    return render(request, 'admin/dashboard.html', context)

# ===============================
# PRODUCT MANAGEMENT
# ===============================
@admin_required
def admin_products(request):
    products = Product.objects.select_related('category').all().order_by('-created_at')
    
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'admin/products.html', context)

@admin_required
def admin_add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        
        category = get_object_or_404(Category, id=category_id)
        
        product = Product.objects.create(
            name=name,
            category=category,
            price=price,
            stock=stock,
            description=description,
            image=image,
            low_stock_threshold=low_stock_threshold
        )
        
        messages.success(request, f'Product "{name}" added successfully!')
        return redirect('admin_products')
    
    categories = Category.objects.filter(is_active=True)
    return render(request, 'admin/add_product.html', {'categories': categories})

@admin_required
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.description = request.POST.get('description')
        product.low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        
        # Fix: Only update image if a new one is uploaded
        if request.FILES.get('image'):
            if product.image:
                try:
                    product.image.delete(save=False)
                except:
                    pass
            product.image = request.FILES.get('image')  # This line was incorrectly indented
        
        product.save()
        messages.success(request, f'Product "{product.name}" updated successfully!')
        return redirect('admin_products')
    
    categories = Category.objects.filter(is_active=True)
    return render(request, 'admin/edit_product.html', {
        'product': product,
        'categories': categories
    })

@admin_required
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product.delete()
    messages.success(request, f'Product "{product_name}" deleted successfully!')
    return redirect('admin_products')

@admin_required
def admin_bulk_stock_update(request):
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        stock_change = int(request.POST.get('stock_change'))
        operation = request.POST.get('operation')
        
        products = Product.objects.filter(id__in=product_ids)
        for product in products:
            if operation == 'add':
                product.stock += stock_change
            elif operation == 'set':
                product.stock = stock_change
            product.save()
        
        messages.success(request, f'Stock updated for {len(products)} products!')
        return redirect('admin_products')
    
    return redirect('admin_products')

# ===============================
# CATEGORY MANAGEMENT
# ===============================
@admin_required
def admin_categories(request):
    categories = Category.objects.all().order_by('-created_at')
    return render(request, 'admin/categories.html', {'categories': categories})

@admin_required
def admin_add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        gst_percent = request.POST.get('gst_percent')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        category = Category.objects.create(
            name=name,
            gst_percent=gst_percent,
            description=description,
            image=image
        )
        
        messages.success(request, f'Category "{name}" added successfully!')
        return redirect('admin_categories')
    
    return render(request, 'admin/add_category.html')

@admin_required
def admin_edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.gst_percent = request.POST.get('gst_percent')
        category.description = request.POST.get('description')
        category.is_active = request.POST.get('is_active') == 'on'
        
        if request.FILES.get('image'):
            category.image = request.FILES.get('image')
        
        category.save()
        messages.success(request, f'Category "{category.name}" updated successfully!')
        return redirect('admin_categories')
    
    return render(request, 'admin/edit_category.html', {'category': category})

@admin_required
def admin_delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category_name = category.name
    category.delete()
    messages.success(request, f'Category "{category_name}" deleted successfully!')
    return redirect('admin_categories')

# ===============================
# ORDER MANAGEMENT
# ===============================
@admin_required
def admin_orders(request):
    orders = Order.objects.select_related('user').all().order_by('-created_at')
    
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    status_counts = {
        'Pending': Order.objects.filter(status='Pending').count(),
        'Processing': Order.objects.filter(status='Processing').count(),
        'Shipped': Order.objects.filter(status='Shipped').count(),
        'Delivered': Order.objects.filter(status='Delivered').count(),
        'Cancelled': Order.objects.filter(status='Cancelled').count(),
    }
    
    context = {
        'orders': orders,
        'status_counts': status_counts,
    }
    return render(request, 'admin/orders.html', context)

@admin_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            if new_status == 'Delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
            order.save()
            messages.success(request, f'Order status updated to {new_status}')
        
        return redirect('admin_order_detail', order_id=order.id)
    
    return render(request, 'admin/order_detail.html', {'order': order})

# ===============================
# CUSTOMER MANAGEMENT
# ===============================
@admin_required
def admin_customers(request):
    customers = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    search = request.GET.get('search')
    if search:
        customers = customers.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    for customer in customers:
        customer.order_count = Order.objects.filter(user=customer).count()
        customer.total_spent = Order.objects.filter(
            user=customer, 
            status='Delivered'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    return render(request, 'admin/customers.html', {'customers': customers})

@admin_required
def admin_customer_detail(request, customer_id):
    customer = get_object_or_404(User, id=customer_id, is_superuser=False)
    orders = Order.objects.filter(user=customer).order_by('-created_at')
    wallet = Wallet.objects.get(user=customer)
    wishlist = Wishlist.objects.filter(user=customer).select_related('product')
    
    context = {
        'customer': customer,
        'orders': orders,
        'wallet': wallet,
        'wishlist': wishlist,
        'order_count': orders.count(),
        'total_spent': orders.filter(status='Delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    return render(request, 'admin/customer_detail.html', context)

# ===============================
# COUPON MANAGEMENT
# ===============================
@admin_required
def admin_coupons(request):
    coupons = Coupon.objects.all().order_by('-created_at')
    return render(request, 'admin/coupons.html', {'coupons': coupons})

@admin_required
def admin_add_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_percent = request.POST.get('discount_percent')
        min_order_amount = request.POST.get('min_order_amount', 0)
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        usage_limit = request.POST.get('usage_limit', 1)
        
        coupon = Coupon.objects.create(
            code=code.upper(),
            discount_percent=discount_percent,
            min_order_amount=min_order_amount,
            valid_from=valid_from,
            valid_to=valid_to,
            usage_limit=usage_limit,
            active=True
        )
        
        messages.success(request, f'Coupon "{code}" created successfully!')
        return redirect('admin_coupons')
    
    return render(request, 'admin/add_coupon.html')

@admin_required
def admin_edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        coupon.code = request.POST.get('code').upper()
        coupon.discount_percent = request.POST.get('discount_percent')
        coupon.min_order_amount = request.POST.get('min_order_amount', 0)
        coupon.valid_from = request.POST.get('valid_from')
        coupon.valid_to = request.POST.get('valid_to')
        coupon.usage_limit = request.POST.get('usage_limit', 1)
        coupon.active = request.POST.get('active') == 'on'
        coupon.save()
        
        messages.success(request, f'Coupon "{coupon.code}" updated successfully!')
        return redirect('admin_coupons')
    
    return render(request, 'admin/edit_coupon.html', {'coupon': coupon})

@admin_required
def admin_delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    code = coupon.code
    coupon.delete()
    messages.success(request, f'Coupon "{code}" deleted successfully!')
    return redirect('admin_coupons')

# ===============================
# PAYMENTS
# ===============================
@admin_required
def admin_payments(request):
    payments = Order.objects.filter(
        status__in=['Delivered', 'Processing', 'Shipped']
    ).order_by('-created_at')
    
    context = {
        'payments': payments,
    }
    return render(request, 'admin/payments.html', context)

# ===============================
# SETTINGS
# ===============================
@admin_required
def admin_settings(request):
    if request.method == 'POST':
        messages.success(request, 'Settings updated successfully!')
        return redirect('admin_settings')
    
    return render(request, 'admin/settings.html')

# ===============================
# ADMIN PROFILE MANAGEMENT
# ===============================

@admin_required
def admin_profile(request):
    """Admin profile page"""
    try:
        admin_profile = request.user.admin_profile
    except AttributeError:
        # Create admin profile if it doesn't exist
        from .models import AdminProfile
        admin_profile = AdminProfile.objects.create(
            user=request.user,
            phone='',
            is_super_admin=True
        )
    
    context = {
        'admin_profile': admin_profile,
    }
    return render(request, 'admin/profile.html', context)


@admin_required
def admin_profile_update(request):
    """Update admin profile information"""
    if request.method == 'POST':
        # Update user information
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Update admin profile
        try:
            admin_profile = request.user.admin_profile
        except AttributeError:
            from .models import AdminProfile
            admin_profile = AdminProfile.objects.create(
                user=request.user,
                is_super_admin=True
            )
        
        admin_profile.phone = request.POST.get('phone', '')
        admin_profile.bio = request.POST.get('bio', '')
        admin_profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('admin_profile')
    
    return redirect('admin_profile')


@admin_required
def admin_change_password(request):
    """Change admin password"""
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Verify current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect!')
            return redirect('admin_profile')
        
        # Check if new password matches confirmation
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match!')
            return redirect('admin_profile')
        
        # Check password length
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return redirect('admin_profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Keep user logged in after password change
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('admin_profile')
    
    return redirect('admin_profile')


@admin_required
def admin_upload_picture(request):
    """Upload admin profile picture"""
    if request.method == 'POST' and request.FILES.get('profile_pic'):
        try:
            admin_profile = request.user.admin_profile
        except AttributeError:
            from .models import AdminProfile
            admin_profile = AdminProfile.objects.create(
                user=request.user,
                is_super_admin=True
            )
        
        # Delete old picture if exists
        if admin_profile.profile_pic:
            admin_profile.profile_pic.delete(save=False)
        
        # Save new picture
        admin_profile.profile_pic = request.FILES['profile_pic']
        admin_profile.save()
        
        messages.success(request, 'Profile picture updated successfully!')
    else:
        messages.error(request, 'No file selected or invalid file.')
    
    return redirect('admin_profile')


@admin_required
def admin_returns(request):
    returns = ReturnRequest.objects.select_related('order', 'product', 'order__user').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        returns = returns.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        returns = returns.filter(
            Q(order__id__icontains=search) |
            Q(product__name__icontains=search) |
            Q(order__user__username__icontains=search)
        )
    
    status_counts = {
        'pending': ReturnRequest.objects.filter(status='pending').count(),
        'approved': ReturnRequest.objects.filter(status='approved').count(),
        'rejected': ReturnRequest.objects.filter(status='rejected').count(),
        'completed': ReturnRequest.objects.filter(status='completed').count(),
    }
    
    context = {
        'returns': returns,
        'status_counts': status_counts,
        'current_status': status_filter,
    }
    return render(request, 'admin/returns.html', context)


@admin_required
def admin_return_detail(request, return_id):
    return_request = get_object_or_404(ReturnRequest.objects.select_related('order', 'product', 'order__user'), id=return_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        refund_amount = request.POST.get('refund_amount')
        admin_notes = request.POST.get('admin_notes')
        
        return_request.status = status
        return_request.admin_notes = admin_notes
        
        if refund_amount:
            return_request.refund_amount = refund_amount
        
        return_request.save()
        
        # Update order
        if status == 'approved':
            return_request.order.return_approved = True
            return_request.order.return_status = 'approved'
            return_request.order.save()
            
            # Process refund to wallet
            if refund_amount:
                wallet, created = Wallet.objects.get_or_create(user=return_request.order.user)
                wallet.balance += Decimal(refund_amount)
                wallet.save()
                
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type='Credit',
                    description=f'Refund for return request #{return_request.id} - Order #{return_request.order.id}',
                    order=return_request.order
                )
                messages.success(request, f'Refund of ₹{refund_amount} processed to customer wallet')
                
        elif status == 'rejected':
            return_request.order.return_approved = False
            return_request.order.return_status = 'rejected'
            return_request.order.save()
        elif status == 'completed':
            return_request.order.return_status = 'completed'
            return_request.order.save()
        
        messages.success(request, f'Return request #{return_request.id} updated to {status}')
        return redirect('admin_returns')
    
    # Calculate refund amount if not set
    if not return_request.refund_amount:
        return_request.refund_amount = return_request.product.price * return_request.quantity
    
    context = {
        'return_request': return_request,
    }
    return render(request, 'admin/return_detail.html', context)


@admin_required
def admin_bulk_approve_returns(request):
    if request.method == 'POST':
        return_ids = request.POST.getlist('return_ids')
        for return_id in return_ids:
            return_request = get_object_or_404(ReturnRequest, id=return_id)
            return_request.status = 'approved'
            return_request.save()
            
            # Process refund
            refund_amount = return_request.product.price * return_request.quantity
            wallet, created = Wallet.objects.get_or_create(user=return_request.order.user)
            wallet.balance += refund_amount
            wallet.save()
            
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=refund_amount,
                transaction_type='Credit',
                description=f'Bulk refund for return request #{return_request.id}',
                order=return_request.order
            )
        
        messages.success(request, f'{len(return_ids)} return requests approved successfully')
        return redirect('admin_returns')
    
    return redirect('admin_returns')


# ===============================
# REPLACEMENT MANAGEMENT
# ===============================
@admin_required
def admin_replacements(request):
    replacements = ReplaceRequest.objects.select_related('order', 'product', 'order__user').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        replacements = replacements.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search')
    if (search):
        replacements = replacements.filter(
            Q(order__id__icontains=search) |
            Q(product__name__icontains=search) |
            Q(order__user__username__icontains=search)
        )
    
    status_counts = {
        'pending': ReplaceRequest.objects.filter(status='pending').count(),
        'approved': ReplaceRequest.objects.filter(status='approved').count(),
        'rejected': ReplaceRequest.objects.filter(status='rejected').count(),
        'completed': ReplaceRequest.objects.filter(status='completed').count(),
    }
    
    context = {
        'replacements': replacements,
        'status_counts': status_counts,
        'current_status': status_filter,
    }
    return render(request, 'admin/replacements.html', context)


@admin_required
def admin_replacement_detail(request, replace_id):
    replace_request = get_object_or_404(ReplaceRequest.objects.select_related('order', 'product', 'order__user'), id=replace_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes')
        
        replace_request.status = status
        replace_request.admin_notes = admin_notes
        replace_request.save()
        
        # Update order
        if status == 'approved':
            replace_request.order.replace_approved = True
            replace_request.order.replace_status = 'approved'
            replace_request.order.save()
        elif status == 'rejected':
            replace_request.order.replace_approved = False
            replace_request.order.replace_status = 'rejected'
            replace_request.order.save()
        elif status == 'completed':
            replace_request.order.replace_status = 'completed'
            replace_request.order.save()
        
        messages.success(request, f'Replacement request #{replace_request.id} updated to {status}')
        return redirect('admin_replacements')
    
    context = {
        'replace_request': replace_request,
    }
    return render(request, 'admin/replacement_detail.html', context)