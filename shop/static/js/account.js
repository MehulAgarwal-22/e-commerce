// ===============================
// ACCOUNT PAGE JAVASCRIPT
// ===============================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functions
    setupPasswordValidation();
    setupFormSubmission();
    setupPhoneValidation();
    loadUserStats();
});

// Password validation and strength checker
function setupPasswordValidation() {
    const newPassword = document.getElementById('newPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    const passwordError = document.getElementById('passwordError');
    const passwordStrength = document.getElementById('passwordStrength');
    const submitBtn = document.getElementById('submitBtn');
    
    if (newPassword && confirmPassword) {
        // Check password strength on input
        newPassword.addEventListener('input', function() {
            const strength = checkPasswordStrength(this.value);
            displayPasswordStrength(strength, passwordStrength);
            
            // Validate match if confirm has value
            if (confirmPassword.value) {
                validatePasswordMatch(newPassword.value, confirmPassword.value, passwordError, submitBtn);
            }
        });
        
        // Check match on confirm password input
        confirmPassword.addEventListener('input', function() {
            validatePasswordMatch(newPassword.value, this.value, passwordError, submitBtn);
        });
    }
}

// Check password strength
function checkPasswordStrength(password) {
    if (!password) return 0;
    
    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;
    
    // Contains number
    if (/\d/.test(password)) strength += 1;
    
    // Contains lowercase
    if (/[a-z]/.test(password)) strength += 1;
    
    // Contains uppercase
    if (/[A-Z]/.test(password)) strength += 1;
    
    // Contains special character
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 1;
    
    return strength;
}

// Display password strength indicator
function displayPasswordStrength(strength, element) {
    if (!element) return;
    
    let strengthText = '';
    let strengthClass = '';
    
    if (strength === 0) {
        strengthText = '';
        strengthClass = '';
    } else if (strength <= 2) {
        strengthText = 'Weak password';
        strengthClass = 'strength-weak';
    } else if (strength <= 4) {
        strengthText = 'Medium password';
        strengthClass = 'strength-medium';
    } else if (strength <= 6) {
        strengthText = 'Strong password';
        strengthClass = 'strength-strong';
    } else {
        strengthText = 'Very strong password';
        strengthClass = 'strength-very-strong';
    }
    
    element.innerHTML = `
        <div class="password-strength ${strengthClass}"></div>
        <small class="text-muted mt-1 d-block">${strengthText}</small>
    `;
}

// Validate password match
function validatePasswordMatch(newPass, confirmPass, errorElement, submitBtn) {
    if (newPass || confirmPass) {
        if (newPass !== confirmPass) {
            errorElement.style.display = 'block';
            if (submitBtn) submitBtn.disabled = true;
            return false;
        } else {
            errorElement.style.display = 'none';
            if (submitBtn) submitBtn.disabled = false;
            return true;
        }
    }
    errorElement.style.display = 'none';
    return true;
}

// Phone number validation
function setupPhoneValidation() {
    const phoneInput = document.querySelector('input[name="phone"]');
    
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            // Allow only numbers
            this.value = this.value.replace(/[^0-9]/g, '');
            
            // Limit to 10 digits
            if (this.value.length > 10) {
                this.value = this.value.slice(0, 10);
            }
        });
    }
}

// Form submission with loading state
function setupFormSubmission() {
    const form = document.getElementById('accountForm');
    const submitBtn = document.getElementById('submitBtn');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            // Check if passwords match
            const newPass = document.getElementById('newPassword')?.value;
            const confirmPass = document.getElementById('confirmPassword')?.value;
            
            if (newPass || confirmPass) {
                if (newPass !== confirmPass) {
                    e.preventDefault();
                    showNotification('Passwords do not match!', 'error');
                    return;
                }
                
                if (newPass && newPass.length < 8) {
                    e.preventDefault();
                    showNotification('Password must be at least 8 characters!', 'error');
                    return;
                }
            }
            
            // Show loading state
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner"></span> Saving...';
                submitBtn.disabled = true;
                
                // Re-enable after 2 seconds (in case of error)
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 2000);
            }
        });
    }
}

// Load user statistics via AJAX
function loadUserStats() {
    // This would typically fetch data from an API
    // For now, we'll just simulate with static data
    console.log('Loading user statistics...');
}

// Show notification messages
function showNotification(message, type = 'success') {
    // Check if SweetAlert2 is available
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: type,
            title: type === 'success' ? 'Success!' : 'Error!',
            text: message,
            timer: 2000,
            showConfirmButton: false,
            position: 'top-end',
            toast: true
        });
    } else {
        alert(message);
    }
}

// Save address as default
function setDefaultAddress(addressId) {
    console.log('Setting default address:', addressId);
    // Implement AJAX call to set default address
}

// Add new address
function addNewAddress() {
    // Implement address modal or redirect
    window.location.href = '/add-address/';
}

// Export functions for global use
window.setDefaultAddress = setDefaultAddress;
window.addNewAddress = addNewAddress;