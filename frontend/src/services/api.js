import axios from 'axios';

// Create an axios instance with default config
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for handling errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// API service object with methods for each endpoint
const apiService = {
  // Opportunities
  getOpportunities: (params) => api.get('/opportunities', { params }),
  getOpportunity: (id) => api.get(`/opportunities/${id}`),
  getOpportunityByReference: (referenceId) => api.get(`/opportunities/reference/${referenceId}`),
  
  // Filters and metadata
  getSources: () => api.get('/sources'),
  getCategories: () => api.get('/categories'),
  getLocations: () => api.get('/locations'),
  
  // Statistics
  getStats: () => api.get('/stats'),
  
  // Admin operations
  runScrape: (data) => api.post('/scrape', data),
};

export default apiService;
