from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models import Avg, Count
from .models import *

# ===============================
# PUBLIC PAGES
# ===============================
def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    
    # Get user's wishlist product IDs
    user_wishlist_ids = []
    if request.user.is_authenticated:
        user_wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        'fruits': products.filter(category__name='Fruits'),
        'vegetables': products.filter(category__name='Vegetables'),
        'bestsellers': products.filter(stock__gt=0)[:6],
        'user_wishlist_ids': list(user_wishlist_ids),
        'wishlist_count': len(user_wishlist_ids),
    })

def shop(request):
    products = Product.objects.all()
    categories = Category.objects.annotate(product_count=Count('product'))
    
    # Get user's wishlist product IDs
    user_wishlist_ids = []
    if request.user.is_authenticated:
        user_wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    # Get filters
    q = request.GET.get('q')
    cat = request.GET.get('category')
    sort = request.GET.get('sort')
    min_p = request.GET.get('min_price')
    max_p = request.GET.get('max_price')
    
    # Apply filters
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat and cat.isdigit():
        products = products.filter(category_id=cat)
    if min_p and min_p.isdigit():
        products = products.filter(price__gte=min_p)
    if max_p and max_p.isdigit():
        products = products.filter(price__lte=max_p)
    
    # Apply sorting
    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')
    
    # Get featured products
    featured_products = Product.objects.filter(stock__gt=0).order_by('?')[:3]
    
    # Pagination
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'shop/shop.html', {
        'products': page_obj,
        'categories': categories,
        'featured_products': featured_products,
        'total_products': Product.objects.count(),
        'user_wishlist_ids': list(user_wishlist_ids),
        'wishlist_count': len(user_wishlist_ids),
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    # Check if product is in user's wishlist
    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    # ========== REVIEW SYSTEM ==========
    # Get average rating and review count
    avg_rating = product.ratings.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_count = product.ratings.count()
    
    # Get all reviews
    reviews = Rating.objects.filter(product=product).order_by('-created_at')
    
    # Check if user can review (has delivered order with this product)
    user_review = None
    can_review = False
    user_order = None
    
    if request.user.is_authenticated:
        user_review = Rating.objects.filter(user=request.user, product=product).first()
        
        # Check if user has purchased and received this product
        delivered_order = Order.objects.filter(
            user=request.user,
            status='Delivered',
            items__product=product
        ).first()
        
        if delivered_order and not user_review:
            can_review = True
            user_order = delivered_order
    
    # Rating distribution for progress bars
    rating_counts = {
        5: product.ratings.filter(rating=5).count(),
        4: product.ratings.filter(rating=4).count(),
        3: product.ratings.filter(rating=3).count(),
        2: product.ratings.filter(rating=2).count(),
        1: product.ratings.filter(rating=1).count(),
    }
    
    # Calculate percentages for progress bars
    rating_percentages = {}
    if rating_count > 0:
        for star in range(1, 6):
            rating_percentages[star] = (rating_counts[star] / rating_count) * 100
    
    context = {
        'product': product,
        'is_in_wishlist': is_in_wishlist,
        # Review data
        'avg_rating': avg_rating,
        'rating_count': rating_count,
        'reviews': reviews,
        'rating_counts': rating_counts,
        'rating_percentages': rating_percentages,
        'user_review': user_review,
        'can_review': can_review,
        'user_order': user_order,
    }
    return render(request, 'shop/product_detail.html', context)


@login_required
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        review = request.POST.get('review', '').strip()
        order_id = request.POST.get('order_id')
        
        # Verify the order belongs to user and is delivered
        if order_id:
            order = get_object_or_404(Order, id=order_id, user=request.user, status='Delivered')
            
            # Verify product was in the order
            if not order.items.filter(product=product).exists():
                messages.error(request, 'You can only review products you have purchased.')
                return redirect('product_detail', pk=product_id)
        else:
            messages.error(request, 'Invalid order.')
            return redirect('product_detail', pk=product_id)
        
        # Create or update review (prevent duplicates)
        rating_obj, created = Rating.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={
                'rating': rating,
                'review': review,
                'order': order,
                'is_verified': True
            }
        )
        
        if created:
            messages.success(request, 'Thank you for your review!')
        else:
            messages.success(request, 'Your review has been updated.')
        
        return redirect('product_detail', pk=product_id)
    
    return redirect('product_detail', pk=product_id)


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Rating, id=review_id, user=request.user)
    product_id = review.product.id
    review.delete()
    messages.success(request, 'Your review has been deleted.')
    return redirect('product_detail', pk=product_id)

# ===============================
# WISHLIST
# ===============================
@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product').order_by('-added_at')
    
    # Pagination for wishlist
    paginator = Paginator(wishlist_items, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'shop/wishlist.html', {
        'wishlist_items': page_obj,
        'wishlist_count': wishlist_items.count(),
    })

@login_required
@require_POST
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product)
    
    if wishlist_item.exists():
        wishlist_item.delete()
        is_in_wishlist = False
        message = 'Removed from wishlist'
    else:
        Wishlist.objects.create(user=request.user, product=product)
        is_in_wishlist = True
        message = 'Added to wishlist'
    
    # Get updated wishlist count
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    # Check if request is AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_in_wishlist': is_in_wishlist,
            'message': message,
            'wishlist_count': wishlist_count,
        })
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'shop'))

@login_required
@require_POST
def remove_from_wishlist(request, wishlist_id):
    wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
    wishlist_item.delete()
    
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Removed from wishlist',
            'wishlist_count': wishlist_count,
        })
    
    messages.success(request, 'Item removed from wishlist')
    return redirect('wishlist')

# ===============================
# CART (AJAX)
# ===============================
@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created and product.stock < item.quantity + quantity:
        return JsonResponse({'success': False, 'error': 'Not enough stock'})
    
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()
    
    cart_count = sum(i.quantity for i in cart.cartitem_set.all())
    return JsonResponse({'success': True, 'cart_count': cart_count})

@login_required
def cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart).select_related('product')
    
    # Calculate subtotal
    subtotal = sum(item.product.price * item.quantity for item in items)
    
    # Free shipping logic (free if subtotal > 500)
    delivery_charge = Decimal('0') if subtotal > 500 else Decimal('50')
    
    # Calculate total
    total = subtotal + delivery_charge
    
    # Calculate amount needed for free shipping
    need_for_free = Decimal('500') - subtotal if subtotal < 500 else Decimal('0')
    
    # Get recommended products (exclude items already in cart)
    cart_product_ids = items.values_list('product_id', flat=True)
    recommended_products = Product.objects.filter(stock__gt=0)\
                                          .exclude(id__in=cart_product_ids)\
                                          .order_by('?')[:4]
    
    # Get user's wishlist for heart icons on recommended products
    user_wishlist_ids = []
    if request.user.is_authenticated:
        user_wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    return render(request, 'shop/cart.html', {
        'items': items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total,
        'need_for_free': need_for_free,
        'item_count': items.count(),
        'recommended_products': recommended_products,
        'user_wishlist_ids': list(user_wishlist_ids),
    })

@login_required
@require_POST
def update_cart(request):
    item = get_object_or_404(CartItem, id=request.POST.get('item_id'), cart__user=request.user)
    action = request.POST.get('action')
    
    if action == "increase":
        if item.quantity < item.product.stock:
            item.quantity += 1
    elif action == "decrease" and item.quantity > 1:
        item.quantity -= 1
    item.save()
    
    cart_items = CartItem.objects.filter(cart=item.cart)
    cart_total = sum(i.product.price * i.quantity for i in cart_items)
    cart_count = sum(i.quantity for i in cart_items)
    
    return JsonResponse({
        'quantity': item.quantity,
        'item_total': float(item.product.price * item.quantity),
        'cart_total': float(cart_total),
        'cart_count': cart_count,
    })

@login_required
@require_POST
def remove_from_cart(request):
    item = get_object_or_404(CartItem, id=request.POST.get('item_id'), cart__user=request.user)
    cart = item.cart
    item.delete()
    
    cart_items = CartItem.objects.filter(cart=cart)
    cart_total = sum(i.product.price * i.quantity for i in cart_items)
    cart_count = sum(i.quantity for i in cart_items)
    
    return JsonResponse({
        'success': True,
        'cart_total': float(cart_total),
        'cart_count': cart_count,
    })

# ===============================
# COUPON
# ===============================
@login_required
@require_POST
def apply_coupon(request):
    code = request.POST.get("code")
    cart = Cart.objects.get(user=request.user)
    items = CartItem.objects.filter(cart=cart)
    
    subtotal = sum(item.product.price * item.quantity for item in items)
    
    try:
        coupon = Coupon.objects.get(code=code, active=True)
        discount = (subtotal * coupon.discount_percent) / 100
        gst = sum((item.product.price * item.quantity * item.product.category.gst_percent) / 100 for item in items)
        delivery = Decimal('50') if subtotal < 500 else Decimal('0')
        total = subtotal - discount + gst + delivery
        
        return JsonResponse({
            "success": True,
            "discount": float(discount),
            "new_total": float(total),
            "message": f"{coupon.discount_percent}% discount applied!"
        })
    except Coupon.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Invalid or expired coupon."
        })

# ===============================
# CHECKOUT & ORDERS
# ===============================
@login_required
@transaction.atomic
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    items = CartItem.objects.filter(cart=cart)
    
    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart")
    
    # Calculate totals
    subtotal = sum(item.product.price * item.quantity for item in items)
    gst_total = sum((item.product.price * item.quantity * item.product.category.gst_percent) / 100 for item in items)
    delivery = Decimal('50') if subtotal < 500 else Decimal('0')
    discount = Decimal('0')
    
    if request.method == "POST":
        coupon_code = request.POST.get("coupon")
        
        # Apply coupon if exists
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, active=True)
                discount = (subtotal * coupon.discount_percent) / 100
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid Coupon Code")
                return redirect("checkout")
        
        grand_total = subtotal + gst_total + delivery - discount
        
        # Check stock
        for item in items:
            if item.product.stock < item.quantity:
                messages.error(request, f"{item.product.name} is out of stock.")
                return redirect("cart")
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            address=request.POST['address'],
            city=request.POST['city'],
            country=request.POST['country'],
            zipcode=request.POST['zipcode'],
            mobile=request.POST['mobile'],
            email=request.POST['email'],
            payment_method=request.POST['payment_method'],
            subtotal=subtotal,
            gst_amount=gst_total,
            delivery_charge=delivery,
            discount_amount=discount,
            coupon_code=coupon_code,
            total_amount=grand_total,
            gst_percent=(gst_total / subtotal * 100) if subtotal > 0 else 0,
            discount_percent=coupon.discount_percent if coupon_code else 0,
        )
        
        # Create order items and reduce stock
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()
        
        items.delete()  # Clear cart
        
        # Send email
        send_mail(
            "Order Confirmed",
            f"Order #{order.id} placed successfully!\nTotal: ₹{grand_total}",
            settings.EMAIL_HOST_USER,
            [order.email],
            fail_silently=True
        )
        
        messages.success(request, "Order placed successfully!")
        return redirect("order_success")
    
    return render(request, "shop/checkout.html", {
        "items": items,
        "subtotal": subtotal,
        "gst": gst_total,
        "delivery": delivery,
        "discount": discount,
        "grand_total": subtotal + gst_total + delivery - discount,
    })

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from .models import Order, Product, ReturnRequest, ReplaceRequest, Rating

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by("-created_at")

    reviewed_product_ids = Rating.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    # Pre-calculate item totals for each order
    for order in orders:
        order_items = []
        for item in order.items.all():
            # Calculate item total here
            item_total = item.price * item.quantity
            order_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'price': item.price,
                'total': item_total,
                'reviewed': item.product.id in reviewed_product_ids,
            })
        order.order_items_with_totals = order_items
    
    return render(request, "shop/order_history.html", {"orders": orders})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status in ['Pending', 'Processing']:
        order.status = 'Cancelled'
        order.save()
        for item in order.items.all():
            item.product.stock += item.quantity
            item.product.save()
        messages.success(request, "Order Cancelled Successfully")
    else:
        messages.error(request, "Order cannot be cancelled")
    return redirect('order_history')

@login_required
def order_success(request):
    return render(request, 'shop/order_success.html')

@login_required
def request_return(request, order_id):
    """Handle return requests - supports both single and multiple items"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method != 'POST':
        return redirect('order_history')
    
    # Get the items data from the request
    items_data = request.POST.get('items_data')
    reason = request.POST.get('reason')
    description = request.POST.get('description', '')
    
    # Check if this is a combined return (multiple items)
    if items_data:
        try:
            items = json.loads(items_data)
            successful_returns = 0
            failed_returns = []
            
            for item_data in items:
                product_id = item_data.get('id')
                quantity = int(item_data.get('quantity', 1))
                
                # Get the product
                product = get_object_or_404(Product, id=product_id)
                
                # Check if product is returnable
                if not product.is_returnable:
                    failed_returns.append(f"{product.name} (not returnable)")
                    continue
                
                # Check if within return window
                if order.delivered_at:
                    days_since_delivery = (timezone.now() - order.delivered_at).days
                    if days_since_delivery > product.return_window_days:
                        failed_returns.append(f"{product.name} (return window expired)")
                        continue
                
                # Check if quantity is valid
                order_item = order.items.filter(product=product).first()
                if order_item and quantity > order_item.quantity:
                    quantity = order_item.quantity
                
                # Create return request for each item
                ReturnRequest.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    reason=reason,
                    description=description,
                    status='pending'
                )
                successful_returns += 1
            
            # Update order status if any returns were successful
            if successful_returns > 0:
                order.return_requested = True
                order.return_reason = reason
                order.return_initiated_at = timezone.now()
                order.save()
                
                if successful_returns == len(items):
                    messages.success(request, f'Return request submitted successfully for {successful_returns} item(s).')
                else:
                    messages.warning(request, f'Return request submitted for {successful_returns} item(s). Failed: {", ".join(failed_returns)}')
            else:
                messages.error(request, f'Unable to process returns. {", ".join(failed_returns)}')
                
        except json.JSONDecodeError:
            messages.error(request, 'Invalid request data.')
        except Exception as e:
            messages.error(request, f'Error processing return request: {str(e)}')
            
    else:
        # Handle single item return (existing functionality)
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        if not product_id:
            messages.error(request, 'Product information missing.')
            return redirect('order_history')
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is returnable
        if not product.is_returnable:
            messages.error(request, 'This product is not eligible for return.')
            return redirect('order_history')
        
        # Check if within return window
        if order.delivered_at:
            days_since_delivery = (timezone.now() - order.delivered_at).days
            if days_since_delivery > product.return_window_days:
                messages.error(request, f'Return window has expired. Returns accepted within {product.return_window_days} days of delivery.')
                return redirect('order_history')
        
        # Create return request
        ReturnRequest.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            reason=reason,
            description=description,
            status='pending'
        )
        
        # Update order
        order.return_requested = True
        order.return_reason = reason
        order.return_initiated_at = timezone.now()
        order.save()
        
        messages.success(request, 'Return request submitted successfully. Our team will review it shortly.')
    
    return redirect('order_history')


@login_required
def request_replace(request, order_id):
    """Handle replacement requests - supports both single and multiple items"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method != 'POST':
        return redirect('order_history')
    
    # Get the items data from the request
    items_data = request.POST.get('items_data')
    reason = request.POST.get('reason')
    description = request.POST.get('description', '')
    
    # Check if this is a combined replacement (multiple items)
    if items_data:
        try:
            items = json.loads(items_data)
            successful_replacements = 0
            failed_replacements = []
            
            for item_data in items:
                product_id = item_data.get('id')
                quantity = int(item_data.get('quantity', 1))
                
                # Get the product
                product = get_object_or_404(Product, id=product_id)
                
                # Check if product is replaceable
                if not product.is_replaceable:
                    failed_replacements.append(f"{product.name} (not replaceable)")
                    continue
                
                # Check if within return window
                if order.delivered_at:
                    days_since_delivery = (timezone.now() - order.delivered_at).days
                    if days_since_delivery > product.return_window_days:
                        failed_replacements.append(f"{product.name} (replacement window expired)")
                        continue
                
                # Check if quantity is valid
                order_item = order.items.filter(product=product).first()
                if order_item and quantity > order_item.quantity:
                    quantity = order_item.quantity
                
                # Create replace request for each item
                ReplaceRequest.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    reason=reason,
                    description=description,
                    status='pending'
                )
                successful_replacements += 1
            
            # Update order status if any replacements were successful
            if successful_replacements > 0:
                order.replace_requested = True
                order.replace_reason = reason
                order.replace_initiated_at = timezone.now()
                order.save()
                
                if successful_replacements == len(items):
                    messages.success(request, f'Replacement request submitted successfully for {successful_replacements} item(s).')
                else:
                    messages.warning(request, f'Replacement request submitted for {successful_replacements} item(s). Failed: {", ".join(failed_replacements)}')
            else:
                messages.error(request, f'Unable to process replacements. {", ".join(failed_replacements)}')
                
        except json.JSONDecodeError:
            messages.error(request, 'Invalid request data.')
        except Exception as e:
            messages.error(request, f'Error processing replacement request: {str(e)}')
            
    else:
        # Handle single item replacement (existing functionality)
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        if not product_id:
            messages.error(request, 'Product information missing.')
            return redirect('order_history')
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is replaceable
        if not product.is_replaceable:
            messages.error(request, 'This product is not eligible for replacement.')
            return redirect('order_history')
        
        # Check if within return window
        if order.delivered_at:
            days_since_delivery = (timezone.now() - order.delivered_at).days
            if days_since_delivery > product.return_window_days:
                messages.error(request, f'Replacement window has expired. Replacements accepted within {product.return_window_days} days of delivery.')
                return redirect('order_history')
        
        # Create replace request
        ReplaceRequest.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            reason=reason,
            description=description,
            status='pending'
        )
        
        # Update order
        order.replace_requested = True
        order.replace_reason = reason
        order.replace_initiated_at = timezone.now()
        order.save()
        
        messages.success(request, 'Replacement request submitted successfully. Our team will review it shortly.')
    
    return redirect('order_history')


# Optional: Add an AJAX endpoint to get return/replace eligibility
@login_required
def check_eligibility(request, order_id):
    """Check which items in an order are eligible for return/replace"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    items_eligibility = []
    for item in order.items.all():
        product = item.product
        eligible = True
        reason = None
        
        # Check if order is delivered
        if order.status != 'Delivered':
            eligible = False
            reason = 'Order not delivered yet'
        
        # Check if product is returnable/replaceable
        elif not (product.is_returnable or product.is_replaceable):
            eligible = False
            reason = 'Product not eligible'
        
        # Check return window
        elif order.delivered_at:
            days_since_delivery = (timezone.now() - order.delivered_at).days
            if days_since_delivery > product.return_window_days:
                eligible = False
                reason = f'Window expired ({product.return_window_days} days)'
        
        items_eligibility.append({
            'id': product.id,
            'name': product.name,
            'quantity': item.quantity,
            'eligible': eligible,
            'reason': reason,
            'is_returnable': product.is_returnable,
            'is_replaceable': product.is_replaceable,
            'return_window_days': product.return_window_days
        })
    
    return JsonResponse({
        'order_id': order.id,
        'status': order.status,
        'delivered_at': order.delivered_at,
        'items': items_eligibility
    })

# ===============================
# AUTH
# ===============================
def register_view(request):
    if request.method == "POST":
        if request.POST['password'] != request.POST['confirm_password']:
            messages.error(request, "Passwords don't match")
            return redirect('register')
        
        if User.objects.filter(username=request.POST['username']).exists():
            messages.error(request, "Username already exists")
            return redirect('register')
        
        user = User.objects.create_user(
            username=request.POST['username'],
            email=request.POST['email'],
            password=request.POST['password']
        )
        login(request, user)
        return redirect('home')
    return render(request, 'registration/register.html')

def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('home')
        messages.error(request, "Invalid credentials")
    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

# ===============================
# USER ACCOUNT
# ===============================
@login_required
def account_details(request):
    # Get counts for sidebar
    orders_count = Order.objects.filter(user=request.user).count()
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    # You can add more stats as needed
    addresses_count = 1  # Default, you can implement address model later
    
    if request.method == "POST":
        # Update user details
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        # Handle password change
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if current_password and new_password and confirm_password:
            if user.check_password(current_password):
                if new_password == confirm_password:
                    if len(new_password) >= 8:
                        user.set_password(new_password)
                        update_session_auth_hash(request, user)  # Keep user logged in
                        messages.success(request, 'Password updated successfully!')
                    else:
                        messages.error(request, 'Password must be at least 8 characters!')
                else:
                    messages.error(request, 'New passwords do not match!')
            else:
                messages.error(request, 'Current password is incorrect!')
        
        user.save()
        
        # You can add profile fields here if you have a Profile model
        # For now, we'll just show success message
        messages.success(request, 'Account details updated successfully!')
        return redirect('account')
    
    context = {
        'orders_count': orders_count,
        'wishlist_count': wishlist_count,
        'addresses_count': addresses_count,
    }
    return render(request, 'shop/account.html', context)

# ===============================
# STATIC PAGES
# ===============================
def contact(request):
    return render(request, 'shop/contact.html')

def about(request):
    return render(request, 'footer/about.html')

def privacy_policy(request):
    return render(request, 'footer/privacy.html')

def terms_of_use(request):
    return render(request, 'footer/terms.html')

def sales_refunds(request):
    return render(request, 'footer/sales_refunds.html')

def faq(request):
    faqs = [
        {'question': 'How can I place an order?', 'answer': 'Browse products, add to cart, and checkout.'},
        {'question': 'What payment methods do you accept?', 'answer': 'Cards, UPI, Net Banking, Wallets.'},
        {'question': 'How can I track my order?', 'answer': 'Check order history for tracking updates.'},
        {'question': 'What is your return policy?', 'answer': 'Returns accepted within 24 hours of delivery.'},
        {'question': 'Can I cancel my order?', 'answer': 'Orders can be cancelled within 1 hour.'},
    ]
    return render(request, 'footer/faq.html', {'faqs': faqs})

# ===============================
# INVOICE
# ===============================
@login_required
def generate_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Fruitables_Invoice_{order.id}.pdf"'
    
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import A4
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    header_style = styles["Heading1"]
    header_style.alignment = 1
    elements.append(Paragraph("FRUITABLES", header_style))
    elements.append(Spacer(1, 20))
    
    # Order info
    elements.append(Paragraph(f"Invoice #{order.id}", styles['Normal']))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%d-%m-%Y')}", styles['Normal']))
    elements.append(Paragraph(f"Customer: {order.first_name} {order.last_name}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Billing Address
    elements.append(Paragraph("<b>Billing Address:</b>", styles['Normal']))
    elements.append(Paragraph(f"{order.address}", styles['Normal']))
    elements.append(Paragraph(f"{order.city}, {order.country} - {order.zipcode}", styles['Normal']))
    elements.append(Paragraph(f"Mobile: {order.mobile}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Items table
    data = [["Product", "Qty", "Price", "Total"]]
    for item in order.items.all():
        data.append([item.product.name, str(item.quantity), f"{item.price:.2f}", f"{item.price * item.quantity:.2f}"])
    
    # Add financial summary
    data.append(["", "", "Subtotal", f"{order.subtotal:.2f}"])
    data.append(["", "", f"GST ({order.gst_percent:.1f}%)", f"{order.gst_amount:.2f}"])
    data.append(["", "", "Delivery", f"{order.delivery_charge:.2f}"])
    if order.discount_amount > 0:
        data.append(["", "", f"Discount ({order.discount_percent:.0f}%)", f"-{order.discount_amount:.2f}"])
    data.append(["", "", "Total", f"{order.total_amount:.2f}"])
    
    table = Table(data, colWidths=[2.5*inch, 1*inch, 1.3*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.green),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Coupon info
    if order.coupon_code:
        elements.append(Paragraph(f"Coupon Applied: {order.coupon_code}", styles['Normal']))
        elements.append(Spacer(1, 10))
    
    # Footer
    elements.append(Paragraph("Thank you for shopping with Fruitables!", styles['Normal']))
    elements.append(Paragraph("For queries: support@fruitables.com", styles['Normal']))
    
    doc.build(elements)
    return response

# ===============================
# SIGNALS
# ===============================
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_related(sender, instance, created, **kwargs):
    if created:
        Cart.objects.get_or_create(user=instance)
        Wallet.objects.get_or_create(user=instance)

        