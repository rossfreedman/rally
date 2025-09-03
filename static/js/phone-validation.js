/**
 * Phone Number Validation and Formatting Utilities
 * ===============================================
 * 
 * Centralized phone number handling for Rally frontend.
 * Ensures consistent phone number formatting and validation across all forms.
 */

/**
 * Format phone number for display (e.g., "(773) 213-8911")
 * @param {string} phone - Phone number in any format
 * @returns {string} Formatted phone number
 */
function formatPhoneForDisplay(phone) {
    if (!phone) return '';
    
    // Remove all non-digit characters
    const digits = phone.replace(/\D/g, '');
    
    // Format based on length
    if (digits.length === 10) {
        return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`;
    } else if (digits.length === 11 && digits.startsWith('1')) {
        // Remove leading 1 and format
        const tenDigits = digits.slice(1);
        return `(${tenDigits.slice(0,3)}) ${tenDigits.slice(3,6)}-${tenDigits.slice(6)}`;
    }
    
    return phone; // Return as-is if not standard format
}

/**
 * Format phone number for input field (real-time formatting)
 * @param {string} value - Current input value
 * @returns {string} Formatted value for input field
 */
function formatPhoneForInput(value) {
    // Remove all non-digit characters
    let digits = value.replace(/\D/g, '');
    
    // Limit to 10 digits (US phone number)
    if (digits.length > 10) {
        digits = digits.slice(0, 10);
    }
    
    // Format based on length
    if (digits.length >= 6) {
        return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`;
    } else if (digits.length >= 3) {
        return `(${digits.slice(0,3)}) ${digits.slice(3)}`;
    } else if (digits.length > 0) {
        return `(${digits}`;
    }
    
    return digits;
}

/**
 * Normalize phone number to E.164 format (+1XXXXXXXXXX)
 * @param {string} phone - Phone number in any format
 * @returns {Object} {success: boolean, normalized: string, error: string}
 */
function normalizePhoneNumber(phone) {
    if (!phone || !phone.trim()) {
        return { success: false, error: 'Phone number is required' };
    }
    
    // Remove all non-digit characters
    const digits = phone.replace(/\D/g, '');
    
    // Validate and normalize
    if (digits.length === 10) {
        // 10 digits: assume US number, add country code
        return { success: true, normalized: `+1${digits}` };
    } else if (digits.length === 11 && digits.startsWith('1')) {
        // 11 digits starting with 1: add + prefix
        return { success: true, normalized: `+${digits}` };
    } else {
        return { 
            success: false, 
            error: `Invalid phone number format. Expected 10 or 11 digits, got ${digits.length}` 
        };
    }
}

/**
 * Validate phone number format
 * @param {string} phone - Phone number to validate
 * @returns {Object} {valid: boolean, error: string}
 */
function validatePhoneNumber(phone) {
    const result = normalizePhoneNumber(phone);
    if (!result.success) {
        return { valid: false, error: result.error };
    }
    
    const normalized = result.normalized;
    
    // Additional validation for US numbers
    if (!normalized.startsWith('+1')) {
        return { valid: false, error: 'Only US phone numbers are supported' };
    }
    
    // Check for valid area code (first 3 digits after +1)
    const areaCode = normalized.slice(2, 5);
    if (areaCode.startsWith('0') || areaCode.startsWith('1')) {
        return { valid: false, error: 'Invalid area code. Area codes cannot start with 0 or 1' };
    }
    
    // Check for valid exchange code (digits 4-6)
    const exchange = normalized.slice(5, 8);
    if (exchange.startsWith('0') || exchange.startsWith('1')) {
        return { valid: false, error: 'Invalid exchange code. Exchange codes cannot start with 0 or 1' };
    }
    
    return { valid: true, error: null };
}

/**
 * Setup phone number input field with real-time formatting
 * @param {string} inputId - ID of the input field
 * @param {Object} options - Configuration options
 */
function setupPhoneInput(inputId, options = {}) {
    const input = document.getElementById(inputId);
    if (!input) {
        console.warn(`Phone input field with ID '${inputId}' not found`);
        return;
    }
    
    const {
        validateOnBlur = true,
        showValidationMessage = true,
        validationMessageId = `${inputId}-error`
    } = options;
    
    // Real-time formatting
    input.addEventListener('input', function() {
        const formatted = formatPhoneForInput(this.value);
        this.value = formatted;
    });
    
    // Validation on blur
    if (validateOnBlur) {
        input.addEventListener('blur', function() {
            const validation = validatePhoneNumber(this.value);
            
            if (showValidationMessage) {
                const errorElement = document.getElementById(validationMessageId);
                if (errorElement) {
                    if (validation.valid) {
                        errorElement.textContent = '';
                        errorElement.classList.add('hidden');
                        input.classList.remove('border-red-500');
                        input.classList.add('border-gray-300');
                    } else {
                        errorElement.textContent = validation.error;
                        errorElement.classList.remove('hidden');
                        input.classList.remove('border-gray-300');
                        input.classList.add('border-red-500');
                    }
                }
            }
        });
    }
}

/**
 * Get normalized phone number from form data
 * @param {string} phoneFieldName - Name of the phone field in form data
 * @param {FormData} formData - Form data object
 * @returns {Object} {success: boolean, normalized: string, error: string}
 */
function getNormalizedPhoneFromForm(phoneFieldName, formData) {
    const phoneValue = formData.get(phoneFieldName);
    return normalizePhoneNumber(phoneValue);
}

/**
 * Setup phone validation for registration form
 * This function handles the specific case where phone numbers need +1 prefix for database storage
 */
function setupRegistrationPhoneHandling() {
    // Find all phone input fields
    const phoneInputs = document.querySelectorAll('input[type="tel"], input[name*="phone"], input[id*="phone"]');
    
    phoneInputs.forEach(input => {
        setupPhoneInput(input.id, {
            validateOnBlur: true,
            showValidationMessage: true
        });
    });
    
    // Override form submission to ensure +1 prefix is added
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const phoneInputs = this.querySelectorAll('input[type="tel"], input[name*="phone"], input[id*="phone"]');
            
            phoneInputs.forEach(input => {
                if (input.value.trim()) {
                    const result = normalizePhoneNumber(input.value);
                    if (result.success) {
                        // Update the input value with normalized phone number
                        input.value = result.normalized;
                    } else {
                        // Show validation error and prevent submission
                        e.preventDefault();
                        alert(`Phone number error: ${result.error}`);
                        input.focus();
                        return false;
                    }
                }
            });
        });
    });
}

/**
 * Initialize phone validation for the current page
 * Call this function when the page loads
 */
function initializePhoneValidation() {
    // Setup phone inputs
    setupRegistrationPhoneHandling();
    
    // Add CSS for validation states
    const style = document.createElement('style');
    style.textContent = `
        .phone-input-error {
            border-color: #ef4444 !important;
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
        }
        .phone-validation-message {
            color: #ef4444;
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }
    `;
    document.head.appendChild(style);
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePhoneValidation);
} else {
    initializePhoneValidation();
}
