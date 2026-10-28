/**
 * Smart Library Management and Book Analytics System
 * Core UI interactions, tooltips, sidebar toggle, and image preview helpers.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Toggle
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            sidebar.classList.toggle('toggled');
        });
    }

    // Close sidebar on mobile when clicking outside
    document.addEventListener('click', function (e) {
        if (window.innerWidth < 992 && sidebar && sidebar.classList.contains('toggled')) {
            if (!sidebar.contains(e.target) && sidebarToggleBtn && !sidebarToggleBtn.contains(e.target)) {
                sidebar.classList.remove('toggled');
            }
        }
    });

    // 2. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // 3. Book Cover Image Upload Preview
    const coverInput = document.getElementById('cover_image');
    const previewContainer = document.getElementById('cover-preview-container');
    const previewImage = document.getElementById('cover-preview-image');

    if (coverInput && previewImage) {
        coverInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                // Check file size (max 2MB)
                if (file.size > 2 * 1024 * 1024) {
                    alert('File size exceeds the 2MB limit. Please select a smaller image.');
                    this.value = '';
                    return;
                }
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewImage.src = e.target.result;
                    if (previewContainer) {
                        previewContainer.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 4. Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
