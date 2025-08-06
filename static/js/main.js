// Global JavaScript functions and utilities

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                submitBtn.disabled = true;
            }
        });
    });

    // Real-time search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }

    // Refresh data every 30 seconds for real-time updates
    if (window.location.pathname.includes('dashboard')) {
        setInterval(refreshDashboardData, 30000);
    }

    // Mobile-friendly table scrolling indicator
    addTableScrollIndicators();
});

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Search functionality
function handleSearch(event) {
    const query = event.target.value.toLowerCase();
    const searchableElements = document.querySelectorAll('.searchable');
    
    searchableElements.forEach(element => {
        const text = element.textContent.toLowerCase();
        const row = element.closest('tr');
        if (row) {
            row.style.display = text.includes(query) ? '' : 'none';
        }
    });
}

// Refresh dashboard data
function refreshDashboardData() {
    if (document.hidden) return; // Don't refresh if tab is not active
    
    fetch(window.location.href, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        const parser = new DOMParser();
        const newDoc = parser.parseFromString(html, 'text/html');
        
        // Update specific sections
        const elementsToUpdate = ['.stats-card', '.table tbody'];
        elementsToUpdate.forEach(selector => {
            const currentElement = document.querySelector(selector);
            const newElement = newDoc.querySelector(selector);
            if (currentElement && newElement) {
                currentElement.innerHTML = newElement.innerHTML;
            }
        });
        
        showToast('Data refreshed', 'info');
    })
    .catch(error => {
        console.error('Error refreshing data:', error);
    });
}

// Toast notifications
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = getOrCreateToastContainer();
    const toastId = 'toast-' + Date.now();
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${getIconForType(type)}"></i> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: duration });
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    return container;
}

function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Confirmation dialogs
function confirmDelete(message = 'Are you sure you want to delete this item?') {
    return new Promise((resolve) => {
        const modal = createConfirmationModal(message);
        document.body.appendChild(modal);
        
        const confirmBtn = modal.querySelector('.btn-confirm');
        const cancelBtn = modal.querySelector('.btn-cancel');
        
        confirmBtn.addEventListener('click', () => {
            resolve(true);
            modal.remove();
        });
        
        cancelBtn.addEventListener('click', () => {
            resolve(false);
            modal.remove();
        });
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    });
}

function createConfirmationModal(message) {
    const modalHTML = `
        <div class="modal fade" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Confirm Action</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-cancel" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-danger btn-confirm">Confirm</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const div = document.createElement('div');
    div.innerHTML = modalHTML;
    return div.firstElementChild;
}

// Table scroll indicators for mobile
function addTableScrollIndicators() {
    const tableContainers = document.querySelectorAll('.table-responsive');
    
    tableContainers.forEach(container => {
        const table = container.querySelector('table');
        if (!table) return;
        
        // Add scroll indicators
        const leftIndicator = document.createElement('div');
        leftIndicator.className = 'scroll-indicator scroll-indicator-left';
        leftIndicator.innerHTML = '<i class="fas fa-chevron-left"></i>';
        
        const rightIndicator = document.createElement('div');
        rightIndicator.className = 'scroll-indicator scroll-indicator-right';
        rightIndicator.innerHTML = '<i class="fas fa-chevron-right"></i>';
        
        container.style.position = 'relative';
        container.appendChild(leftIndicator);
        container.appendChild(rightIndicator);
        
        // Update indicator visibility
        function updateIndicators() {
            const scrollLeft = container.scrollLeft;
            const scrollWidth = container.scrollWidth;
            const clientWidth = container.clientWidth;
            
            leftIndicator.style.display = scrollLeft > 0 ? 'block' : 'none';
            rightIndicator.style.display = scrollLeft < (scrollWidth - clientWidth) ? 'block' : 'none';
        }
        
        container.addEventListener('scroll', updateIndicators);
        window.addEventListener('resize', updateIndicators);
        updateIndicators();
    });
}

// Enhanced delete functionality with confirmation
window.deleteWithConfirmation = async function(url, message) {
    const confirmed = await confirmDelete(message);
    if (confirmed) {
        window.location.href = url;
    }
};

// Form validation enhancement
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(form)) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        }
    });
    
    return isValid;
}

// Initialize form validation
document.addEventListener('DOMContentLoaded', enhanceFormValidation);