// SmartPip Authentication JavaScript

class AuthManager {
    constructor() {
        this.isLoginMode = true;
        this.apiBase = window.location.origin + '/api';
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkAuth();
    }
    
    setupEventListeners() {
        // Toggle between login and signup
        document.getElementById('toggleAuth').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAuthMode();
        });
        
        // Form submission
        document.getElementById('authForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });
        
        // Forgot password
        document.getElementById('forgotPassword').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleForgotPassword();
        });
    }
    
    toggleAuthMode() {
        this.isLoginMode = !this.isLoginMode;
        
        const title = document.getElementById('authTitle');
        const subtitle = document.getElementById('authSubtitle');
        const submitBtn = document.getElementById('authSubmit');
        const toggleText = document.getElementById('authToggle');
        const toggleLink = document.getElementById('toggleAuth');
        const nameGroup = document.getElementById('nameGroup');
        const confirmGroup = document.getElementById('confirmPasswordGroup');
        const apiTokenGroup = document.getElementById('apiTokenGroup');
        
        if (this.isLoginMode) {
            title.textContent = 'Login';
            subtitle.textContent = 'Sign in to your trading account';
            submitBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
            toggleText.innerHTML = "Don't have an account? <a href='#' id='toggleAuth'>Sign up</a>";
            nameGroup.style.display = 'none';
            confirmGroup.style.display = 'none';
            apiTokenGroup.style.display = 'none';
        } else {
            title.textContent = 'Sign Up';
            subtitle.textContent = 'Create your trading account';
            submitBtn.innerHTML = '<i class="fas fa-user-plus"></i> Sign Up';
            toggleText.innerHTML = "Already have an account? <a href='#' id='toggleAuth'>Login</a>";
            nameGroup.style.display = 'block';
            confirmGroup.style.display = 'block';
            apiTokenGroup.style.display = 'block';
        }
        
        // Re-attach event listener to toggle link
        document.getElementById('toggleAuth').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAuthMode();
        });
    }
    
    async handleSubmit() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        if (this.isLoginMode) {
            await this.login(email, password);
        } else {
            const fullName = document.getElementById('fullName').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const apiToken = document.getElementById('apiToken').value;
            
            await this.signup(fullName, email, password, confirmPassword, apiToken);
        }
    }
    
    async login(email, password) {
        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.apiBase}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Store token
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                
                this.showToast('Login successful', 'success');
                
                // Redirect to main app
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                this.showToast(data.message || 'Login failed', 'error');
            }
        } catch (error) {
            this.showToast('Login failed. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async signup(fullName, email, password, confirmPassword, apiToken) {
        // Validation
        if (!fullName) {
            this.showToast('Please enter your full name', 'error');
            return;
        }
        
        if (password !== confirmPassword) {
            this.showToast('Passwords do not match', 'error');
            return;
        }
        
        if (password.length < 8) {
            this.showToast('Password must be at least 8 characters', 'error');
            return;
        }
        
        if (!apiToken) {
            this.showToast('Please enter your Deriv API token', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.apiBase}/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    full_name: fullName,
                    email,
                    password,
                    api_token: apiToken
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast('Account created successfully', 'success');
                
                // Switch to login mode
                this.toggleAuthMode();
            } else {
                this.showToast(data.message || 'Signup failed', 'error');
            }
        } catch (error) {
            this.showToast('Signup failed. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleForgotPassword() {
        const email = document.getElementById('email').value;
        
        if (!email) {
            this.showToast('Please enter your email address', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.apiBase}/auth/forgot-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast('Password reset link sent to your email', 'success');
            } else {
                this.showToast(data.message || 'Failed to send reset link', 'error');
            }
        } catch (error) {
            this.showToast('Failed to send reset link. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    checkAuth() {
        const token = localStorage.getItem('token');
        
        if (token) {
            // User is authenticated, redirect to main app
            window.location.href = '/';
        }
    }
    
    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/auth.html';
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

// Initialize auth manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});
