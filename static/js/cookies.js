// Cookie consent handling

document.addEventListener('DOMContentLoaded', function() {
    const cookieBanner = document.getElementById('cookie-banner');
    const acceptBtn = document.getElementById('accept-cookies');
    const declineBtn = document.getElementById('decline-cookies');

    // Check if user has already responded to cookie consent
    const cookieConsent = getCookie('cookie_consent');

    if (!cookieConsent) {
        // Show banner if no consent recorded
        cookieBanner.style.display = 'block';
    }

    // Accept cookies
    acceptBtn.addEventListener('click', function() {
        setCookie('cookie_consent', 'accepted', 365);
        cookieBanner.style.display = 'none';

        // Send consent to server
        fetch('/cookie-consent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    });

    // Decline cookies
    declineBtn.addEventListener('click', function() {
        setCookie('cookie_consent', 'declined', 365);
        cookieBanner.style.display = 'none';
    });
});

// Helper function to get a cookie
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Helper function to set a cookie
function setCookie(name, value, days) {
    let expires = '';
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = '; expires=' + date.toUTCString();
    }
    document.cookie = name + '=' + (value || '') + expires + '; path=/; SameSite=Lax';
}
