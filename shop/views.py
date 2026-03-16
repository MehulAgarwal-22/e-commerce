from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
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
    
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'is_in_wishlist': is_in_wishlist,
    })

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

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
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
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != "Delivered":
        messages.error(request, "Return is only allowed for delivered orders.")
        return redirect("order_history")
    
    if order.delivered_at and timezone.now() > order.delivered_at + timedelta(days=24):
        messages.error(request, "Return window has expired.")
        return redirect("order_history")
    
    order.return_requested = True
    order.save()
    messages.success(request, "Return request submitted successfully.")
    return redirect("order_history")

@login_required
def request_replace(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != "Delivered":
        messages.error(request, "Replacement is only allowed for delivered orders.")
        return redirect("order_history")
    
    if order.delivered_at and timezone.now() > order.delivered_at + timedelta(days=24):
        messages.error(request, "Replacement window has expired.")
        return redirect("order_history")
    
    order.replace_requested = True
    order.save()
    messages.success(request, "Replacement request submitted successfully.")
    return redirect("order_history")

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
    if request.method == "POST":
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        messages.success(request, "Account updated successfully!")
        return redirect('account')
    return render(request, 'shop/account.html')

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