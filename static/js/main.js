// Global JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length >= 10) {
                value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
            }
            e.target.value = value;
        });
    });

    // File upload preview
    const photoInput = document.getElementById('photo');
    if (photoInput) {
        photoInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    let preview = document.getElementById('photo-preview');
                    if (!preview) {
                        preview = document.createElement('img');
                        preview.id = 'photo-preview';
                        preview.className = 'img-thumbnail mt-2';
                        preview.style.maxWidth = '200px';
                        preview.style.maxHeight = '200px';
                        photoInput.parentNode.appendChild(preview);
                    }
                    preview.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Location autocomplete enhancement
    const locationInputs = document.querySelectorAll('input[name="location"]');
    locationInputs.forEach(function(input) {
        let debounceTimer;
        input.addEventListener('input', function(e) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                const value = e.target.value;
                if (value.length > 2) {
                    // Add loading indicator
                    e.target.classList.add('loading-bg');
                    
                    // This would integrate with a location API
                    // For now, just remove loading after delay
                    setTimeout(function() {
                        e.target.classList.remove('loading-bg');
                    }, 1000);
                }
            }, 300);
        });
    });
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
    const phoneRegex = /^\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$/;
    return phoneRegex.test(phone);
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(function() {
        notification.remove();
    }, 5000);
}

// Map utilities
function initializeMap(elementId, centerLat = 39.8283, centerLng = -98.5795, zoom = 4) {
    const map = L.map(elementId).setView([centerLat, centerLng], zoom);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    return map;
}

function addMarkerToMap(map, lat, lng, popupText, iconColor = 'blue') {
    const marker = L.marker([lat, lng], {
        icon: L.icon({
            iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${iconColor}.png`,
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
        });
    } else {
        // Fallback to copying URL
        navigator.clipboard.writeText(caseUrl).then(function() {
            showNotification('Case URL copied to clipboard!', 'success');
        });
    }
}
