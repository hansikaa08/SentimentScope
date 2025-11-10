import { apiRequest, TokenManager, validateEmail, validatePassword } from './utils.js';

export class AuthService {
    static async register(userData) {
        if (!validateEmail(userData.email)) {
            throw new Error('Please enter a valid email address');
        }
        
        if (!validatePassword(userData.password)) {
            throw new Error('Password must be at least 8 characters long');
        }
        
        const result = await apiRequest('/auth/register', {
            method: 'POST',
            body: userData
        });
        
        return result;
    }
    
    static async verifyEmail(verificationData) {
        const result = await apiRequest('/auth/verify', {
            method: 'POST',
            body: verificationData
        });
        
        return result;
    }
    
    static async login(credentials) {
        if (!validateEmail(credentials.email)) {
            throw new Error('Please enter a valid email address');
        }
        
        const result = await apiRequest('/auth/login', {
            method: 'POST',
            body: credentials
        });
        
        if (result.token) {
            TokenManager.setToken(result.token);
            TokenManager.setUser(result.user);
        }
        
        return result;
    }
    
    static logout() {
        TokenManager.removeToken();
        window.location.href = 'login.html';
    }
    
    static getCurrentUser() {
        return TokenManager.getUser();
    }
    
    static isLoggedIn() {
        return TokenManager.isAuthenticated();
    }
    
    static requireAuth() {
        if (!this.isLoggedIn()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }
}