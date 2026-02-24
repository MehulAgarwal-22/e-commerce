from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from django.db.models.signals import post_save
from django.dispatch import receiver

from django.core.mail import send_mail
from django.conf import settings

from reportlab.pdfgen import canvas
from django.http import HttpResponse

from .models import Product, Order, OrderItem, Cart, CartItem, Wishlist, Coupon, Wallet


# ===============================
# HOME
# ===============================
def home(request):
    products = Product.objects.all()
    return render(request, 'shop/home.html', {'products': products})


# ===============================
# SHOP PAGE
# ===============================
def shop(request):
    products = Product.objects.all()
    return render(request, 'shop/shop.html', {'products': products})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_detail.html', {
        'product': product
    })


# ===============================
# ADD TO CART (AJAX)
# ===============================
@login_required
@require_POST
def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart, created = Cart.objects.get_or_create(user=request.user)

    quantity = int(request.POST.get('quantity', 1))

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not created:
        if product.stock < item.quantity + quantity:
            return JsonResponse({
                "success": False,
                "error": "Not enough stock"
            })
        item.quantity += quantity
    else:
        item.quantity = quantity

    item.save()

    cart_count = sum(i.quantity for i in cart.cartitem_set.all())

    return JsonResponse({
        "success": True,
        "cart_count": cart_count
    })

# ===============================
# ORDER HISTORY
# ===============================
@login_required
def order_history(request):
    orders = Order.objects.filter(email=request.user.email).order_by('-created_at')

    return render(request, 'shop/order_history.html', {
        'orders': orders
    })


# ===============================
# ACCOUNT DETAILS
# ===============================
@login_required
def account_details(request):

    if request.method == "POST":
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.save()

        messages.success(request, "Account updated successfully!")
        return redirect('account')

    return render(request, 'shop/account.html')


# ===============================
# CART PAGE
# ===============================
@login_required
def cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart)

    total = sum(item.product.price * item.quantity for item in items)

    return render(request, 'shop/cart.html', {
        'items': items,
        'total': total
    })


# ===============================
# UPDATE CART (AJAX + / -)
# ===============================
@login_required
@require_POST
def update_cart(request):
    item_id = request.POST.get('item_id')
    action = request.POST.get('action')

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    if action == "increase":
        item.quantity += 1
    elif action == "decrease":
        if item.quantity > 1:
            item.quantity -= 1

    item.save()

    item_total = item.product.price * item.quantity
    cart_total = sum(
        i.product.price * i.quantity
        for i in item.cart.cartitem_set.all()
    )

    cart_count = sum(
        i.quantity
        for i in item.cart.cartitem_set.all()
    )

    return JsonResponse({
        'quantity': item.quantity,
        'item_total': float(item_total),
        'cart_total': float(cart_total),
        'cart_count': cart_count
    })

# =========================
# AUTO CREATE CART
# =========================
@receiver(post_save, sender=User)
def create_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)

# ===============================
# REMOVE FROM CART (AJAX)
# ===============================
@login_required
@require_POST
def remove_from_cart(request):
    item_id = request.POST.get('item_id')

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart = item.cart
    item.delete()

    cart_total = sum(
        i.product.price * i.quantity
        for i in cart.cartitem_set.all()
    )

    cart_count = sum(
        i.quantity
        for i in cart.cartitem_set.all()
    )

    return JsonResponse({
        'success': True,
        'cart_total': float(cart_total),
        'cart_count': cart_count
    })


# ===============================
# CHECKOUT
# ===============================
@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)

@login_required
def checkout(request):

    cart = Cart.objects.get(user=request.user)
    items = CartItem.objects.filter(cart=cart)

    total = sum(item.product.price * item.quantity for item in items)

    if request.method == "POST":

        payment_method = request.POST.get("payment_method")

        # WALLET PAYMENT
        if payment_method == "Wallet":
            wallet = Wallet.objects.get(user=request.user)

            if wallet.balance < total:
                messages.error(request, "Insufficient wallet balance")
                return redirect("checkout")

            wallet.balance -= total
            wallet.save()

        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            country=request.POST.get('country'),
            zipcode=request.POST.get('zipcode'),
            mobile=request.POST.get('mobile'),
            email=request.POST.get('email'),
            payment_method=payment_method,
            total_amount=total
        )

        for item in items:
            if item.product.stock < item.quantity:
                messages.error(request, f"{item.product.name} is out of stock.")
                return redirect("cart")
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            item.product.stock -= item.quantity
            item.product.save()

        items.delete()

        # EMAIL CONFIRMATION
        send_mail(
            "Order Confirmation",
            f"Your Order #{order.id} has been placed successfully.",
            settings.EMAIL_HOST_USER,
            [order.email],
            fail_silently=True
        )

        messages.success(request, "Order placed successfully!")
        return redirect("order_success")

    return render(request, "shop/checkout.html", {
        "items": items,
        "total": total
    })



@login_required
@require_POST
def apply_coupon(request):
    code = request.POST.get('coupon_code')

    try:
        coupon = Coupon.objects.get(code=code, active=True)
        request.session['coupon'] = coupon.code
        messages.success(request, "Coupon Applied!")
    except Coupon.DoesNotExist:
        messages.error(request, "Invalid Coupon Code")

    return redirect('checkout')

@login_required
def order_success(request):
    return render(request, 'shop/order_success.html')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "shop/order_history.html", {"orders": orders})


# ===============================
# AUTH SYSTEM
# ===============================
def register_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(request, user)
        return redirect('home')

    return render(request, 'registration/register.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


# ===============================
# STATIC PAGES
# ===============================
def contact(request):
    return render(request, 'shop/contact.html')


def privacy_policy(request):
    return render(request, 'footer/privacy.html')


def terms_of_use(request):
    return render(request, 'footer/terms.html')


def sales_refunds(request):
    return render(request, 'footer/sales_refunds.html')

from django.shortcuts import render

def faq(request):
    # You can later fetch these from DB
    faqs = [
        {
            'question': 'How can I place an order?',
            'answer': 'Browse our products, add items to your cart, and click the checkout button. Fill in your shipping details and payment method to place your order.'
        },
        {
            'question': 'What payment methods do you accept?',
            'answer': 'We accept credit/debit cards, net banking, UPI, and popular wallets like Paytm, PhonePe, and Google Pay.'
        },
        {
            'question': 'How can I track my order?',
            'answer': 'Once your order is shipped, you will receive an email or SMS with a tracking number. Use it to track your order on our website or the courier partner’s website.'
        },
        {
            'question': 'What is your return/exchange policy?',
            'answer': 'If you receive damaged or incorrect items, contact our support within 24 hours with order details. We will arrange a replacement or refund.'
        },
        {
            'question': 'Can I cancel my order?',
            'answer': 'Orders can be canceled within 1 hour of placing them. After that, cancellation is subject to processing status.'
        },
        {
            'question': 'How do I create or manage my account?',
            'answer': 'Click on the account icon, sign up with your email, and fill in your details. You can manage your orders, addresses, and preferences from your account dashboard.'
        },
        {
            'question': 'How can I contact customer support?',
            'answer': 'Email: support@fruitables.com | Phone: (+012) 3456 7890'
        },
    ]
    return render(request, 'footer/faq.html', {'faqs': faqs})

def about(request):
    return render(request, 'footer/about.html')

def wishlist(request):
    if request.user.is_authenticated:
        wishlist_items = Wishlist.objects.filter(user=request.user)
    else:
        wishlist_items = []
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def generate_invoice(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    p = canvas.Canvas(response)

    p.drawString(100, 800, f"Invoice - Order #{order.id}")
    p.drawString(100, 780, f"Customer: {order.first_name}")
    p.drawString(100, 760, f"Total: ₹{order.total_amount}")
    p.drawString(100, 740, f"Status: {order.status}")

    y = 700
    for item in order.items.all():
        p.drawString(100, y, f"{item.product.name} x {item.quantity}")
        y -= 20

    p.showPage()
    p.save()

    return response