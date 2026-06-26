// SmartPip Authentication — redirects to React app auth
// This page is deprecated. Use the React dashboard at / instead.

class AuthManager {
    constructor() {
        this.init();
    }

    init() {
        // Redirect to the main React app which has proper Supabase Auth
        window.location.href = '/';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});
