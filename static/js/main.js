// Enhanced JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 8 seconds with fade effect
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(function() {
                const closeButton = alert.querySelector('.btn-close');
                if (closeButton) {
                    closeButton.click();
                }
            }, 300);
        }, 8000);
    });

    // Enhanced form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Find first invalid field and focus it
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            form.classList.add('was-validated');
        });

        // Real-time validation feedback
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(function(input) {
            input.addEventListener('blur', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });

    // Enhanced phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            
            if (value.length >= 10) {
                if (value.length === 10) {
                    value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
                } else if (value.length === 11 && value[0] === '1') {
                    value = value.replace(/(\d{1})(\d{3})(\d{3})(\d{4})/, '+$1 ($2) $3-$4');
                }
            }
            e.target.value = value;
        });

        // Add country code prefix for international numbers
        input.addEventListener('focus', function() {
            if (!this.value && !this.placeholder.includes('+')) {
                this.placeholder = '+1 (555) 123-4567';
            }
        });
    });

    // Enhanced file upload preview with progress
    const photoInput = document.getElementById('photo');
    if (photoInput) {
        photoInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                // Validate file type
                const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
                if (!validTypes.includes(file.type)) {
                    showNotification('Please select a valid image file (JPEG, PNG, GIF)', 'danger');
                    this.value = '';
                    return;
                }

                // Validate file size (16MB)
                if (file.size > 16 * 1024 * 1024) {
                    showNotification('File size must be less than 16MB', 'danger');
                    this.value = '';
                    return;
                }

                const reader = new FileReader();
                reader.onload = function(e) {
                    let preview = document.getElementById('photo-preview');
                    if (!preview) {
                        preview = document.createElement('div');
                        preview.id = 'photo-preview';
                        preview.className = 'mt-3';
                        photoInput.parentNode.appendChild(preview);
                    }
                    
                    preview.innerHTML = `
                        <div class="card">
                            <div class="card-body text-center">
                                <img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">
                                <p class="mt-2 mb-0 text-muted">
                                    <i class="fas fa-file-image me-1"></i>
                                    ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)
                                </p>
                            </div>
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Enhanced location autocomplete with loading states
    const locationInputs = document.querySelectorAll('input[name="location"]');
    locationInputs.forEach(function(input) {
        let debounceTimer;
        let isLoading = false;

        input.addEventListener('input', function(e) {
            clearTimeout(debounceTimer);
            const value = e.target.value.trim();
            
            if (value.length > 2 && !isLoading) {
                // Add loading indicator
                addLoadingState(this);
                
                debounceTimer = setTimeout(() => {
                    geocodeLocation(value, this);
                }, 500);
            } else if (value.length <= 2) {
                removeLoadingState(this);
                hideMap();
            }
        });

        function addLoadingState(inputElement) {
            isLoading = true;
            inputElement.style.background = 'url("image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTQiIGN5PSIxMCIgcj0iMiIgZmlsbD0iIzMzNzNkYyI+CjxhbmltYXRlIGF0dHJpYnV0ZU5hbWU9Im9wYWNpdHkiIGZyb209IjEiIHRvPSIwIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIvPgo8L2NpcmNsZT4KPC9zdmc+") no-repeat right 12px center';
            inputElement.style.backgroundSize = '16px 16px';
        }

        function removeLoadingState(inputElement) {
            isLoading = false;
            inputElement.style.background = '';
        }
    });

    // Smooth scrolling for anchor links
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

    // Lazy loading for images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Add copy to clipboard functionality
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            showNotification('Copied to clipboard!', 'success');
        }).catch(function() {
            showNotification('Failed to copy to clipboard', 'danger');
        });
    };
});

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function validatePhoneNumber(phone) {
    const phoneRegex = /^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$/;
    return phoneRegex.test(phone);
}

function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.toast-notification');
    existingNotifications.forEach(n => n.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed toast-notification`;
    notification.style.cssText = `
        top: 100px; 
        right: 20px; 
        z-index: 9999; 
        min-width: 300px; 
        max-width: 400px;
        box-shadow: var(--shadow-lg);
        border: none;
        animation: slideInRight 0.3s ease-out;
    `;
    
    const iconMap = {
        'success': 'fa-check-circle',
        'danger': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    
    notification.innerHTML = `
        <i class="fas ${iconMap[type] || 'fa-info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after specified duration
    setTimeout(function() {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// Map utilities
function initializeMap(elementId, centerLat = 39.8283, centerLng = -98.5795, zoom = 4) {
    const map = L.map(elementId, {
        zoomControl: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        dragging: true
    }).setView([centerLat, centerLng], zoom);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    return map;
}

function addMarkerToMap(map, lat, lng, popupText, iconColor = 'blue') {
    const iconUrls = {
        'red': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
        'green': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
        'blue': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
        'orange': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
        'violet': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-violet.png'
    };

    const marker = L.marker([lat, lng], {
        icon: L.icon({
            iconUrl: iconUrls[iconColor] || iconUrls['blue'],
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        })
    }).addTo(map);
    
    if (popupText) {
        marker.bindPopup(popupText);
    }
    
    return marker;
}

// Emergency contact functionality
function callEmergency() {
    if (confirm('This will attempt to call emergency services. Continue?')) {
        window.location.href = 'tel:911';
    }
}

// Share functionality
function shareCase(caseUrl, caseName) {
    if (navigator.share) {
        navigator.share({
            title: `Missing Child Alert - ${caseName}`,
            text: `Please help find ${caseName}. Every share could help bring them home safely.`,
            url: caseUrl
        }).catch(console.error);
    } else {
        // Fallback to copying URL
        navigator.clipboard.writeText(caseUrl).then(function() {
            showNotification('Case URL copied to clipboard! Share it to help find this child.', 'success');
        }).catch(function() {
            showNotification('Failed to copy URL. Please copy it manually from the address bar.', 'warning');
        });
    }
}

// Print functionality
function printCase() {
    window.print();
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .loading-bg {
        background-color: #f8f9fa !important;
        background-image: linear-gradient(45deg, transparent 35%, rgba(255,255,255,0.5) 50%, transparent 65%);
        background-size: 20px 20px;
        animation: loading-animation 1s linear infinite;
    }
    
    @keyframes loading-animation {
        0% { background-position: 0% 0%; }
        100% { background-position: 20px 0%; }
    }
`;
document.head.appendChild(style);
