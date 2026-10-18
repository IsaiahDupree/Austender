/**
 * Frontend Application Configuration
 */

// API URL
export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Feature flags
export const FEATURES = {
  NOTIFICATIONS: true,  // Enable notification subscriptions
  ANALYTICS: true,      // Enable analytics features
  DOCUMENT_ANALYSIS: true, // Enable document analysis features
  ADVANCED_SEARCH: true // Enable advanced search features
};

// Number of items to display per page
export const ITEMS_PER_PAGE = 10;

// Theme configuration
export const THEME_CONFIG = {
  PRIMARY_COLOR: '#2a5885',
  SECONDARY_COLOR: '#f50057',
  DARK_MODE: false
};
