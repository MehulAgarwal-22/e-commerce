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
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `quantity=${quantity}`
    })
    .then(response => {

        // 🚀 IF REDIRECT (Not Logged In)
        if (response.redirected) {
            window.location.href = response.url;
            return null;
        }

        // 🚀 IF RESPONSE IS NOT JSON
        if (!response.ok) {
            throw new Error("Not JSON response");
        }

        return response.json();
    })
    .then(data => {

        if (!data) return;

        if (data.success) {

            let badge = document.getElementById("cart-count");
            if (badge) {
                badge.innerText = data.cart_count;
            }

            alert("Added to cart successfully!");
        }

    })
    .catch(error => {
        console.log("Add To Cart Error:", error);
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