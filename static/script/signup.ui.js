/**
 * Sign-up UI Handler
 * Manages responsive layout transitions and submission feedback.
 */

function adjustSignupLayout() {
    const isMobile = window.innerHeight > window.innerWidth;
    const decorativeImg = document.getElementById('img');
    const signupForm = document.querySelector('form');

    if (isMobile) {
        // Mobile View: Center the form and hide the decorative GIF
        if (decorativeImg) {
            decorativeImg.style.display = 'none';
        }
        if (signupForm) {
            signupForm.style.position = 'relative';
            signupForm.style.left = '0';
            signupForm.style.margin = '20px auto';
            signupForm.style.width = '90%';
            signupForm.style.top = '5vh';
        }
    } else {
        // Desktop View: Restore split-screen layout
        if (decorativeImg) {
            decorativeImg.style.display = 'block';
        }
        if (signupForm) {
            signupForm.style.position = 'absolute';
            signupForm.style.left = '65%';
            signupForm.style.width = '250px';
            signupForm.style.top = '10vh';
        }
    }
}

// Initialize layout immediately to avoid flickering
adjustSignupLayout();

// Listen for orientation changes or window resizing
window.addEventListener('resize', adjustSignupLayout);

// Provide visual feedback during registration
document.querySelector('form').addEventListener('submit', function() {
    const signupBtn = document.getElementById('frm-btn');
    if (signupBtn) {
        signupBtn.innerText = "Creating Account...";
        signupBtn.disabled = true;
        signupBtn.style.opacity = "0.7";
    }
});