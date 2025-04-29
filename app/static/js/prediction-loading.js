document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('predictionForm');
    const loadingSpinner = document.getElementById('loadingSpinner');

    if (form) {
        form.addEventListener('submit', function() {
            // Hide form and show loading spinner
            form.style.display = 'none';
            if (loadingSpinner) {
                loadingSpinner.style.display = 'block';
            }
        });
    }
});
