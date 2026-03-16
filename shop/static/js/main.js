(function ($) {
    "use strict";

    // ===============================
    // TEMPLATE CODE
    // ===============================

    // Spinner
    var spinner = function () {
        setTimeout(function () {
            if ($('#spinner').length > 0) {
                $('#spinner').removeClass('show');
            }
        }, 1);
    };
    spinner(0);

    // Fixed Navbar
    $(window).scroll(function () {
        if ($(window).width() < 992) {
            if ($(this).scrollTop() > 55) {
                $('.fixed-top').addClass('shadow');
            } else {
                $('.fixed-top').removeClass('shadow');
            }
        } else {
            if ($(this).scrollTop() > 55) {
                $('.fixed-top').addClass('shadow').css('top', -55);
            } else {
                $('.fixed-top').removeClass('shadow').css('top', 0);
            }
        }
    });

    // Back to top
    $(window).scroll(function () {
        if ($(this).scrollTop() > 300) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });

    $('.back-to-top').click(function () {
        $('html, body').animate({ scrollTop: 0 }, 1500, 'easeInOutExpo');
        return false;
    });

    // Owl Carousel
    $(".vegetable-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1500,
        center: false,
        dots: true,
        loop: true,
        margin: 25,
        nav: true,
        navText: [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ],
        responsive: {
            0:{ items:1 },
            576:{ items:1 },
            768:{ items:2 },
            992:{ items:3 },
            1200:{ items:4 }
        }
    });

})(jQuery);



/* =====================================================
   ================= CART SYSTEM =======================
   ===================================================== */


// ===============================
// GET CSRF TOKEN
// ===============================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie("csrftoken");


// ===============================
// INCREASE QTY (HOME / SHOP)
// ===============================
window.increaseQty = function(productId) {
    let input = document.getElementById("qty-" + productId);
    if (input) {
        input.value = parseInt(input.value) + 1;
    }
};


// ===============================
// DECREASE QTY (HOME / SHOP)
// ===============================
window.decreaseQty = function(productId) {
    let input = document.getElementById("qty-" + productId);
    if (input && parseInt(input.value) > 1) {
        input.value = parseInt(input.value) - 1;
    }
};


// ===============================
// ADD TO CART
// ===============================
window.addToCart = function(productId) {
    let qtyInput = document.getElementById("qty-" + productId);
    let quantity = qtyInput ? qtyInput.value : 1;

    fetch(`/add-to-cart/${productId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `quantity=${quantity}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let badge = document.getElementById("cart-count");
            if (badge) {
                badge.innerText = data.cart_count;
            }
            showAlert('Product added to cart!', true);
        } else {
            showAlert(data.error || 'Error adding to cart', false);
        }
    })
    .catch(error => {
        showAlert('Error adding to cart', false);
    });
};


// ===============================
// UPDATE CART (inside cart page)
// ===============================
window.updateQuantity = function(itemId, action) {

    fetch(`/update-cart/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `item_id=${itemId}&action=${action}`
    })
    .then(response => response.json())
    .then(data => {

        let qtyInput = document.getElementById("qty-" + itemId);
        if (qtyInput) qtyInput.value = data.quantity;

        let totalSpan = document.getElementById("total-" + itemId);
        if (totalSpan) totalSpan.innerText = data.item_total;

        let cartTotal = document.getElementById("cart-total");
        if (cartTotal) cartTotal.innerText = data.cart_total;

        let badge = document.getElementById("cart-count");
        if (badge) badge.innerText = data.cart_count;
    })
    .catch(error => {
        console.log("Error:", error);
    });
};


// ===============================
// REMOVE FROM CART
// ===============================
window.removeItem = function(itemId) {

    fetch(`/remove-from-cart/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `item_id=${itemId}`
    })
    .then(response => response.json())
    .then(data => {

        let row = document.getElementById("row-" + itemId);
        if (row) row.remove();

        let cartTotal = document.getElementById("cart-total");
        if (cartTotal) cartTotal.innerText = data.cart_total;

        let badge = document.getElementById("cart-count");
        if (badge) badge.innerText = data.cart_count;

        if (data.cart_count === 0) {
            location.reload();
        }
    })
    .catch(error => {
        console.log("Error:", error);
    });
};

window.applyCoupon = function() {

    let code = document.getElementById("coupon-code").value;

    fetch("/apply-coupon/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: "code=" + code
    })
    .then(response => response.json())
    .then(data => {

        let messageBox = document.getElementById("coupon-message");

        if (data.success) {

            messageBox.innerHTML = data.message;
            messageBox.classList.remove("text-danger");
            messageBox.classList.add("text-success");

            // ✅ UPDATE DISCOUNT
            document.getElementById("discount-amount").innerText = data.discount.toFixed(2);

            // ✅ UPDATE TOTAL
            document.getElementById("final-total").innerText = data.new_total.toFixed(2);

        } else {

            messageBox.innerHTML = data.message;
            messageBox.classList.remove("text-success");
            messageBox.classList.add("text-danger");
        }
    });
}

function showAlert(message, isSuccess = true) {
    Swal.fire({
        icon: isSuccess ? 'success' : 'error',
        title: isSuccess ? 'Success!' : 'Error!',
        text: message,
        timer: 2000,
        showConfirmButton: false,
        position: 'top-end',
        toast: true
    });
}

// ===============================
// CART PAGE FUNCTIONS
// ===============================

// Get CSRF token
function getCsrfToken() {
    return document.getElementById('csrf-token')?.value || getCookie('csrftoken');
}

// Update quantity in cart
window.updateQuantity = function(itemId, action) {
    fetch('/update-cart/', {
        method: "POST",
        headers: {
            "X-CSRFToken": getCsrfToken(),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `item_id=${itemId}&action=${action}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Update quantity
        const qtyInput = document.getElementById("qty-"+itemId);
        qtyInput.value = data.quantity;
        
        // Update item total
        document.getElementById("total-"+itemId).innerText = data.item_total.toFixed(2);
        
        // Update cart totals
        updateCartTotals(data.cart_total, data.cart_count);
        
        // FIX: Update button states based on new quantity
        const row = document.getElementById("row-"+itemId);
        const minusBtn = row.querySelector('button[onclick*="decrease"]');
        const plusBtn = row.querySelector('button[onclick*="increase"]');
        const maxStock = parseInt(plusBtn.getAttribute('data-max-stock') || '999');
        
        // Enable/disable minus button based on quantity
        if (data.quantity <= 1) {
            minusBtn.disabled = true;
        } else {
            minusBtn.disabled = false;
        }
        
        // Enable/disable plus button based on stock
        if (data.quantity >= maxStock) {
            plusBtn.disabled = true;
        } else {
            plusBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error updating cart');
    });
};

// Remove item from cart
window.removeItem = function(itemId) {
    fetch('/remove-from-cart/', {
        method: "POST",
        headers: {
            "X-CSRFToken": getCsrfToken(),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `item_id=${itemId}`
    })
    .then(response => response.json())
    .then(data => {
        // Remove row
        document.getElementById("row-"+itemId).remove();
        
        // Update cart totals
        updateCartTotals(data.cart_total, data.cart_count);
        
        // If cart is empty, reload
        if (data.cart_count === 0) {
            location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error removing item');
    });
};

// Update cart totals
function updateCartTotals(subtotal, count) {
    // Update subtotal
    document.getElementById('cart-subtotal').innerText = subtotal.toFixed(2);
    document.getElementById('item-count').innerText = count;
    
    // Calculate delivery
    let delivery = subtotal > 500 ? 0 : 50;
    let deliveryElement = document.getElementById('delivery-charge');
    
    if (delivery === 0) {
        deliveryElement.innerHTML = '<span class="text-success">Free</span>';
    } else {
        deliveryElement.innerText = '₹' + delivery.toFixed(2);
    }
    
    // Update total
    let total = subtotal + delivery;
    document.getElementById('cart-total').innerText = total.toFixed(2);
    
    // Update cart badge
    let badge = document.getElementById('cart-count');
    if (badge) badge.innerText = count;
}

// Quick add to cart from related products - FIXED for immediate update
window.quickAddToCart = function(button) {
    const productId = button.getAttribute('data-product-id');
    const originalText = button.innerHTML;
    
    button.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Adding...';
    button.disabled = true;
    
    fetch(`/add-to-cart/${productId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCsrfToken(),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: 'quantity=1'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update cart badge immediately
            let badge = document.getElementById('cart-count');
            if (badge) {
                badge.innerText = data.cart_count;
                // Add visual feedback
                badge.style.transform = 'scale(1.2)';
                setTimeout(() => {
                    badge.style.transform = 'scale(1)';
                }, 200);
            }
            
            // Show success on button
            button.innerHTML = '<i class="fa fa-check"></i> Added!';
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-success');
            
            // Reset button after delay
            setTimeout(() => {
                button.innerHTML = '<i class="fa fa-shopping-bag me-2"></i>Add to Cart';
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-primary');
                button.disabled = false;
            }, 1500);
            
            // If we're on the cart page, we need to update the cart display
            // Check if we have cart items table
            if (document.querySelector('.table')) {
                // Refresh the page to show new item in cart
                // This ensures cart items are updated
                setTimeout(() => {
                    location.reload();
                }, 500);
            }
        } else {
            alert(data.error || 'Error adding to cart');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error adding to cart');
        button.innerHTML = originalText;
        button.disabled = false;
    });
};

// Helper function (already in your main.js)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===============================
// WISHLIST FUNCTIONS
// ===============================

// Toggle wishlist (add/remove)
window.toggleWishlist = function(button, productId) {
    // Prevent default actions
    event.preventDefault();
    event.stopPropagation();
    
    const icon = button.querySelector('i');
    const originalClass = icon.className;
    
    // Show loading
    icon.className = 'fa fa-spinner fa-spin text-primary';
    button.disabled = true;
    
    fetch(`/toggle-wishlist/${productId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update heart icon
            if (data.is_in_wishlist) {
                icon.className = 'fa fa-heart text-danger';
                // Add animation
                button.style.transform = 'scale(1.2)';
                setTimeout(() => {
                    button.style.transform = 'scale(1)';
                }, 200);
                
                // Show success message
                if (typeof showToast === 'function') {
                    showToast('Added to wishlist', 'success');
                }
            } else {
                icon.className = 'fa fa-heart text-muted';
                // Add animation
                button.style.transform = 'scale(1.2)';
                setTimeout(() => {
                    button.style.transform = 'scale(1)';
                }, 200);
                
                if (typeof showToast === 'function') {
                    showToast('Removed from wishlist', 'success');
                }
            }
            
            // Update wishlist count in navbar
            const wishlistBadge = document.getElementById('wishlist-count');
            if (wishlistBadge) {
                wishlistBadge.style.transform = 'scale(1.2)';
                wishlistBadge.innerText = data.wishlist_count;
                
                // Hide badge if count is 0
                if (data.wishlist_count === 0) {
                    wishlistBadge.style.display = 'none';
                } else {
                    wishlistBadge.style.display = 'flex';
                }
                
                setTimeout(() => {
                    wishlistBadge.style.transform = 'scale(1)';
                }, 200);
            }
        } else {
            icon.className = originalClass;
            if (typeof showToast === 'function') {
                showToast(data.message || 'Error updating wishlist', 'error');
            } else {
                alert('Error updating wishlist');
            }
        }
        button.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        icon.className = originalClass;
        button.disabled = false;
        if (typeof showToast === 'function') {
            showToast('Error updating wishlist', 'error');
        } else {
            alert('Error updating wishlist');
        }
    });
};

// ===============================
// QUANTITY FUNCTIONS
// ===============================

window.decreaseQty = function(productId) {
    const input = document.getElementById('qty-' + productId);
    const currentVal = parseInt(input.value);
    if (currentVal > 1) {
        input.value = currentVal - 1;
    }
};

window.increaseQty = function(productId) {
    const input = document.getElementById('qty-' + productId);
    const currentVal = parseInt(input.value);
    const max = parseInt(input.getAttribute('data-max-stock') || '999');
    if (currentVal < max) {
        input.value = currentVal + 1;
    }
};

// ===============================
// ADD TO CART FUNCTION
// ===============================

window.addToCart = function(productId) {
    const button = event.target.closest('button');
    const originalHtml = button.innerHTML;
    const qtyInput = document.getElementById('qty-' + productId);
    const quantity = qtyInput ? qtyInput.value : 1;
    
    // Show loading
    button.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Adding...';
    button.disabled = true;
    
    fetch(`/add-to-cart/${productId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `quantity=${quantity}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update cart count
            const cartBadge = document.getElementById('cart-count');
            if (cartBadge) {
                cartBadge.style.transform = 'scale(1.2)';
                cartBadge.innerText = data.cart_count;
                setTimeout(() => {
                    cartBadge.style.transform = 'scale(1)';
                }, 200);
            }
            
            // Show success on button
            button.innerHTML = '<i class="fa fa-check"></i> Added!';
            button.classList.remove('btn-primary');
            button.classList.add('btn-success');
            
            setTimeout(() => {
                button.innerHTML = originalHtml;
                button.classList.remove('btn-success');
                button.classList.add('btn-primary');
                button.disabled = false;
            }, 1500);
            
            // Show toast if available
            if (typeof showToast === 'function') {
                showToast('Product added to cart!', 'success');
            }
        } else {
            button.innerHTML = originalHtml;
            button.disabled = false;
            if (typeof showToast === 'function') {
                showToast(data.error || 'Error adding to cart', 'error');
            } else {
                alert(data.error || 'Error adding to cart');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        button.innerHTML = originalHtml;
        button.disabled = false;
        if (typeof showToast === 'function') {
            showToast('Error adding to cart', 'error');
        } else {
            alert('Error adding to cart');
        }
    });
};

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}