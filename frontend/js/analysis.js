import { apiRequest, TokenManager } from './utils.js';
import { AuthService } from './auth.js';

export class AnalysisService {
    static async analyzeProduct(productName) {
        if (!AuthService.isLoggedIn()) {
            throw new Error('Please log in to analyze products');
        }
        
        const result = await apiRequest('/api/analyze-product', {
            method: 'POST',
            body: { product_name: productName }
        });
        
        return result;
    }
    
    static displayResults(analysisResult) {
        return analysisResult;
    }
}