/**
 * Sign-in UI Handler
 * Ensures the login form is perfectly centered on mobile and desktop.
 */

function adjustLayout() {
    const isMobile = window.innerHeight > window.innerWidth;
    const decorativeImg = document.getElementById('img');
    const loginForm = document.querySelector('form');

    if (isMobile) {
        // Mobile View Optimization
        if (decorativeImg) {
            decorativeImg.style.display = 'none';
        }
        if (loginForm) {
            loginForm.style.position = 'relative';
            loginForm.style.left = '0';
            loginForm.style.margin = '20px auto';
            loginForm.style.width = '90%';
            loginForm.style.top = '5vh';
        }
    } else {
        // Desktop View Restoration
        if (decorativeImg) {
            decorativeImg.style.display = 'block';
        }
        if (loginForm) {
            loginForm.style.position = 'absolute';
            loginForm.style.left = '65%';
            loginForm.style.width = '250px';
            loginForm.style.top = '10vh';
        }
    }
}

// Execute immediately to prevent layout flickering
adjustLayout();

// Re-adjust if the user rotates their phone
window.addEventListener('resize', adjustLayout);

// Form Submission Feedback
document.querySelector('form').addEventListener('submit', function() {
    const btn = document.getElementById('frm-btn');
    if (btn) {
        btn.innerText = "Checking...";
        btn.style.opacity = "0.7";
    }
});