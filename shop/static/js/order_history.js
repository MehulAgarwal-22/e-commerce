// ===============================
// ORDER HISTORY PAGE FUNCTIONS
// ===============================

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add cancel confirmation to all cancel buttons
    setupCancelConfirmation();
    
    // Add responsive table handling
    setupResponsiveTables();
    
    // Add tooltips for better UX
    setupTooltips();
    
    // Initialize combined return/replace functionality
    initCombinedActions();
    
    // Initialize select all checkboxes
    initSelectAllCheckboxes();
    
    // Add animation to order cards
    animateOrderCards();
});

// ===============================
// COMBINED RETURN/REPLACE FUNCTIONS (Amazon-style)
// ===============================

// Initialize combined actions for all orders
function initCombinedActions() {
    // Setup return selected buttons
    const returnButtons = document.querySelectorAll('.btn-return-selected');
    returnButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const orderId = this.dataset.orderId;
            handleBulkAction(orderId, 'return');
        });
    });
    
    // Setup replace selected buttons
    const replaceButtons = document.querySelectorAll('.btn-replace-selected');
    replaceButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const orderId = this.dataset.orderId;
            handleBulkAction(orderId, 'replace');
        });
    });
    
    // Setup individual checkboxes
    const checkboxes = document.querySelectorAll('.item-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const orderId = this.dataset.orderId;
            updateSelectedCount(orderId);
            updateActionButtonsState(orderId);
        });
    });
}

// Handle bulk return/replace action
function handleBulkAction(orderId, actionType) {
    const selectedItems = getSelectedItems(orderId);
    
    if (selectedItems.length === 0) {
        Swal.fire({
            title: 'No Items Selected',
            text: `Please select at least one item to ${actionType}.`,
            icon: 'warning',
            confirmButtonColor: '#82c440'
        });
        return;
    }
    
    // Show confirmation dialog
    const actionText = actionType === 'return' ? 'Return' : 'Replace';
    const itemList = selectedItems.map(item => `• ${item.name} (Qty: ${item.quantity})`).join('<br>');
    
    Swal.fire({
        title: `${actionText} Selected Items?`,
        html: `
            <p>You are about to request ${actionText.toLowerCase()} for:</p>
            <div style="text-align: left; background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                ${itemList}
            </div>
            <p>Total items: ${selectedItems.length}</p>
        `,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: actionType === 'return' ? '#ffc107' : '#17a2b8',
        cancelButtonColor: '#6c757d',
        confirmButtonText: `Yes, ${actionText} Items`,
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show modal for reason selection
            showActionModal(orderId, actionType, selectedItems);
        }
    });
}

// Show modal for return/replace reason
function showActionModal(orderId, actionType, selectedItems) {
    const modalId = actionType === 'return' ? `combinedReturnModal${orderId}` : `combinedReplaceModal${orderId}`;
    const modal = document.getElementById(modalId);
    
    if (modal) {
        // Populate modal with selected items
        const itemsListDiv = document.getElementById(`${actionType}ItemsList${orderId}`);
        const itemsDataInput = document.getElementById(`${actionType}ItemsData${orderId}`);
        
        if (itemsListDiv && itemsDataInput) {
            let html = '<div class="selected-items-summary">';
            html += '<h6 class="mb-3">Selected Items:</h6>';
            html += '<div class="list-group mb-3">';
            selectedItems.forEach(item => {
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${escapeHtml(item.name)}</strong>
                                <br>
                                <small class="text-muted">Quantity: ${item.quantity}</small>
                            </div>
                            <div class="item-quantity-input" data-item-id="${item.id}">
                                <label class="small">Qty to ${actionType}:</label>
                                <input type="number" 
                                       class="form-control form-control-sm" 
                                       style="width: 80px;" 
                                       value="${item.quantity}" 
                                       min="1" 
                                       max="${item.quantity}"
                                       data-item-id="${item.id}">
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            itemsListDiv.innerHTML = html;
            
            // Store selected items data
            itemsDataInput.value = JSON.stringify(selectedItems.map(item => ({
                id: item.id,
                name: item.name,
                quantity: item.quantity
            })));
            
            // Add quantity change handlers
            document.querySelectorAll(`#${actionType}ItemsList${orderId} .item-quantity-input input`).forEach(input => {
                input.addEventListener('change', function() {
                    updateItemQuantity(orderId, actionType, this.dataset.itemId, this.value);
                });
            });
        }
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Update item quantity in modal
function updateItemQuantity(orderId, actionType, itemId, newQuantity) {
    const itemsDataInput = document.getElementById(`${actionType}ItemsData${orderId}`);
    if (itemsDataInput) {
        let itemsData = JSON.parse(itemsDataInput.value);
        const itemIndex = itemsData.findIndex(item => item.id == itemId);
        if (itemIndex !== -1) {
            itemsData[itemIndex].quantity = parseInt(newQuantity);
            itemsDataInput.value = JSON.stringify(itemsData);
        }
    }
}

// Get selected items for an order
function getSelectedItems(orderId) {
    const checkboxes = document.querySelectorAll(`.item-${orderId}`);
    const selected = [];
    
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selected.push({
                id: checkbox.dataset.itemId,
                name: checkbox.dataset.itemName,
                quantity: checkbox.dataset.quantity
            });
        }
    });
    
    return selected;
}

// Update selected items count display
function updateSelectedCount(orderId) {
    const selectedItems = getSelectedItems(orderId);
    const count = selectedItems.length;
    
    const selectedCountSpan = document.getElementById(`selectedCount${orderId}`);
    if (selectedCountSpan) {
        selectedCountSpan.textContent = `${count} item${count !== 1 ? 's' : ''}`;
        selectedCountSpan.style.fontWeight = count > 0 ? 'bold' : 'normal';
    }
    
    return selectedItems;
}

// Update action buttons state based on selection
function updateActionButtonsState(orderId) {
    const selectedCount = getSelectedItems(orderId).length;
    const returnBtn = document.querySelector(`.btn-return-selected[data-order-id="${orderId}"]`);
    const replaceBtn = document.querySelector(`.btn-replace-selected[data-order-id="${orderId}"]`);
    
    if (returnBtn) {
        if (selectedCount === 0) {
            returnBtn.disabled = true;
            returnBtn.style.opacity = '0.5';
        } else {
            returnBtn.disabled = false;
            returnBtn.style.opacity = '1';
        }
    }
    
    if (replaceBtn) {
        if (selectedCount === 0) {
            replaceBtn.disabled = true;
            replaceBtn.style.opacity = '0.5';
        } else {
            replaceBtn.disabled = false;
            replaceBtn.style.opacity = '1';
        }
    }
}

// Initialize select all checkboxes functionality
function initSelectAllCheckboxes() {
    const selectAllCheckboxes = document.querySelectorAll('.select-all-checkbox');
    
    selectAllCheckboxes.forEach(selectAll => {
        selectAll.addEventListener('change', function() {
            const orderId = this.dataset.orderId;
            const itemCheckboxes = document.querySelectorAll(`.item-${orderId}`);
            
            itemCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            
            updateSelectedCount(orderId);
            updateActionButtonsState(orderId);
        });
    });
}

// ===============================
// EXISTING FUNCTIONS (Enhanced)
// ===============================

// Setup cancel confirmation with SweetAlert
function setupCancelConfirmation() {
    const cancelButtons = document.querySelectorAll('a[href*="cancel_order"]');
    
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            Swal.fire({
                title: 'Cancel Order?',
                text: 'Are you sure you want to cancel this order? This action cannot be undone.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                cancelButtonColor: '#6c757d',
                confirmButtonText: 'Yes, cancel it!',
                cancelButtonText: 'No, keep it'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = this.href;
                }
            });
        });
    });
}

// Setup responsive tables (add data-label attributes for mobile)
function setupResponsiveTables() {
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
        const headers = [];
        table.querySelectorAll('thead th').forEach(header => {
            headers.push(header.textContent.trim());
        });
        
        table.querySelectorAll('tbody tr').forEach(row => {
            row.querySelectorAll('td').forEach((cell, index) => {
                cell.setAttribute('data-label', headers[index] || '');
            });
        });
    });
}

// Setup tooltips
function setupTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'custom-tooltip';
            tooltip.textContent = this.getAttribute('data-tooltip');
            tooltip.style.position = 'absolute';
            tooltip.style.background = '#333';
            tooltip.style.color = 'white';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '12px';
            tooltip.style.zIndex = '1000';
            tooltip.style.pointerEvents = 'none';
            
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                delete this._tooltip;
            }
        });
    });
}

// Function to show order details modal
function showOrderDetails(orderId) {
    Swal.fire({
        title: `Order Details - #${orderId}`,
        html: `
            <div class="text-start">
                <p><strong>Order ID:</strong> ${orderId}</p>
                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                <p><strong>Status:</strong> <span class="badge bg-success">Delivered</span></p>
                <hr>
                <p><strong>Items:</strong></p>
                <ul>
                    <li>Product 1 - Qty: 2 - ₹999</li>
                    <li>Product 2 - Qty: 1 - ₹499</li>
                </ul>
                <hr>
                <p><strong>Total:</strong> ₹1498</p>
            </div>
        `,
        icon: 'info',
        confirmButtonColor: '#82c440'
    });
}

// Function to track order
function trackOrder(orderId) {
    Swal.fire({
        title: 'Track Order',
        html: `
            <div class="tracking-info">
                <div class="timeline">
                    <div class="timeline-item">
                        <i class="fas fa-check-circle text-success"></i>
                        <span>Order Placed - March 22, 2026</span>
                    </div>
                    <div class="timeline-item">
                        <i class="fas fa-check-circle text-success"></i>
                        <span>Shipped - March 23, 2026</span>
                    </div>
                    <div class="timeline-item">
                        <i class="fas fa-truck"></i>
                        <span>Out for Delivery - March 24, 2026</span>
                    </div>
                </div>
            </div>
        `,
        icon: 'info',
        confirmButtonColor: '#82c440',
        confirmButtonText: 'Track on Map'
    }).then((result) => {
        if (result.isConfirmed) {
            // Add tracking map logic here
            Swal.fire('Tracking Info', 'Your order is out for delivery!', 'info');
        }
    });
}

// Function to reorder
function reorder(orderId) {
    Swal.fire({
        title: 'Reorder?',
        text: 'Would you like to add all items from this order to your cart?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#82c440',
        confirmButtonText: 'Yes, reorder',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show loading state
            Swal.fire({
                title: 'Adding to Cart...',
                text: 'Please wait while we add items to your cart',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Simulate API call
            setTimeout(() => {
                Swal.fire({
                    title: 'Success!',
                    text: 'Items added to your cart successfully!',
                    icon: 'success',
                    timer: 1500,
                    showConfirmButton: false
                });
            }, 1000);
        }
    });
}

// Add smooth scrolling for better UX
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add animation on scroll for order cards
function animateOrderCards() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.order-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.5s ease';
        observer.observe(card);
    });
}

// Helper function to escape HTML
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Export functions if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        setupCancelConfirmation,
        setupResponsiveTables,
        showOrderDetails,
        trackOrder,
        reorder,
        handleBulkAction,
        getSelectedItems,
        updateSelectedCount
    };
}