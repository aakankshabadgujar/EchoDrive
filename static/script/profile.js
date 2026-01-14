/**
 * Triggers the file upload process with validation and user feedback.
 * Aligned with Project Specification Section 9.98 (Upload feedback).
 */
function frm_s() {
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');
    const uploadButton = document.querySelector('button[type="submit"]');

    // 1. Validation: Check if files are selected
    if (!fileInput || fileInput.files.length === 0) {
        alert("Please select at least one file to upload.");
        return;
    }

    // 2. UX Feedback: Update button state to prevent double-submissions
    if (uploadButton) {
        uploadButton.disabled = true;
        uploadButton.innerText = "Uploading " + fileInput.files.length + " file(s)...";
        uploadButton.style.opacity = "0.6";
        uploadButton.style.cursor = "not-allowed";
    }

    // 3. Form Submission: Send data to the Flask /upload/<username> route
    try {
        console.log("Submitting form with " + fileInput.files.length + " files.");
        uploadForm.submit();
    } catch (error) {
        console.error("Upload failed:", error);
        alert("An error occurred during upload. Please try again.");
        
        // Reset UI if submission fails
        if (uploadButton) {
            uploadButton.disabled = false;
            uploadButton.innerText = "Upload to Cloud";
            uploadButton.style.opacity = "1";
            uploadButton.style.cursor = "pointer";
        }
    }
}

/**
 * Event Listener for automatic upload.
 * Triggers as soon as files are chosen in the file dialog.
 */
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Auto-trigger the upload function once selection is made
                frm_s();
            }
        });
    }
});