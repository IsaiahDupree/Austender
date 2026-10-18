import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Paper, 
  Grid, 
  FormControl, 
  FormLabel, 
  RadioGroup, 
  Radio, 
  FormControlLabel,
  Chip,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Checkbox,
  ListItemText,
  Snackbar,
  Alert
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import axios from 'axios';
import { API_URL } from '../config';

// Location options for select dropdown
const LOCATIONS = [
  'Sydney',
  'Melbourne',
  'Brisbane',
  'Perth',
  'Adelaide',
  'Canberra',
  'Hobart',
  'Darwin',
  'Regional NSW',
  'Regional VIC',
  'Regional QLD',
  'Regional WA',
  'Regional SA',
  'Regional TAS',
  'Regional NT',
  'Multiple Locations',
  'National',
];

// Source options for select dropdown
const SOURCES = [
  'Austender',
  'ANI',
  'ICN',
  'SAM',
];

// Notification frequency options
const NOTIFICATION_FREQUENCIES = [
  { value: 'immediate', label: 'Immediate (As soon as opportunities arrive)' },
  { value: 'daily', label: 'Daily Summary' },
  { value: 'weekly', label: 'Weekly Summary' },
];

const SubscriptionForm = () => {
  const theme = useTheme();
  
  // Form state
  const [formState, setFormState] = useState({
    email: '',
    name: '',
    notificationFrequency: 'daily',
    keywords: [],
    locations: [],
    sources: [],
    capitalValueMin: '',
    capitalValueMax: '',
  });
  
  // UI state
  const [keywordInput, setKeywordInput] = useState('');
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });
  
  // Handle text input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormState({
      ...formState,
      [name]: value
    });
    
    // Clear error for this field if it exists
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: null
      });
    }
  };
  
  // Handle multi-select changes
  const handleMultiSelectChange = (event, field) => {
    const { 
      target: { value },
    } = event;
    
    setFormState({
      ...formState,
      [field]: typeof value === 'string' ? value.split(',') : value,
    });
  };
  
  // Add keyword from input
  const handleAddKeyword = () => {
    if (keywordInput.trim() !== '' && !formState.keywords.includes(keywordInput.trim())) {
      setFormState({
        ...formState,
        keywords: [...formState.keywords, keywordInput.trim()]
      });
      setKeywordInput('');
    }
  };
  
  // Remove keyword
  const handleRemoveKeyword = (keyword) => {
    setFormState({
      ...formState,
      keywords: formState.keywords.filter(k => k !== keyword)
    });
  };
  
  // Validate form
  const validateForm = () => {
    const newErrors = {};
    
    if (!formState.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formState.email)) {
      newErrors.email = 'Email is invalid';
    }
    
    if (!formState.name) {
      newErrors.name = 'Name is required';
    }
    
    if (formState.capitalValueMin && isNaN(Number(formState.capitalValueMin))) {
      newErrors.capitalValueMin = 'Must be a number';
    }
    
    if (formState.capitalValueMax && isNaN(Number(formState.capitalValueMax))) {
      newErrors.capitalValueMax = 'Must be a number';
    }
    
    if (formState.capitalValueMin && formState.capitalValueMax && 
        Number(formState.capitalValueMin) > Number(formState.capitalValueMax)) {
      newErrors.capitalValueMax = 'Maximum value must be greater than minimum value';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Submit form
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    // Prepare data for API
    const subscriptionData = {
      email: formState.email,
      name: formState.name,
      notification_frequency: formState.notificationFrequency,
      filters: {
        keywords: formState.keywords.length > 0 ? formState.keywords : null,
        location: formState.locations.length > 0 ? formState.locations : null,
        source: formState.sources.length > 0 ? formState.sources : null,
        capital_value_min: formState.capitalValueMin ? Number(formState.capitalValueMin) : null,
        capital_value_max: formState.capitalValueMax ? Number(formState.capitalValueMax) : null,
      }
    };
    
    setIsSubmitting(true);
    
    try {
      // Send to API
      const response = await axios.post(`${API_URL}/subscriptions`, subscriptionData, {
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': process.env.REACT_APP_API_KEY || 'api-key-placeholder'
        }
      });
      
      // Success
      setSnackbar({
        open: true,
        message: 'Subscription created successfully!',
        severity: 'success'
      });
      
      // Reset form
      setFormState({
        email: '',
        name: '',
        notificationFrequency: 'daily',
        keywords: [],
        locations: [],
        sources: [],
        capitalValueMin: '',
        capitalValueMax: '',
      });
      
    } catch (error) {
      console.error('Error creating subscription:', error);
      
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Error creating subscription',
        severity: 'error'
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 4, 
        mt: 4, 
        backgroundColor: theme.palette.background.paper,
        borderRadius: 2
      }}
    >
      <Typography variant="h5" gutterBottom>
        Subscribe to Opportunity Notifications
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 3, color: theme.palette.text.secondary }}>
        Stay updated on construction opportunities matching your criteria
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit} noValidate>
        <Grid container spacing={3}>
          {/* Contact Information */}
          <Grid item xs={12}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Contact Information
            </Typography>
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              value={formState.email}
              onChange={handleInputChange}
              error={!!errors.email}
              helperText={errors.email}
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              required
              fullWidth
              id="name"
              label="Your Name"
              name="name"
              value={formState.name}
              onChange={handleInputChange}
              error={!!errors.name}
              helperText={errors.name}
            />
          </Grid>
          
          {/* Notification Preferences */}
          <Grid item xs={12}>
            <Typography variant="h6" sx={{ mt: 2, mb: 2 }}>
              Notification Preferences
            </Typography>
          </Grid>
          
          <Grid item xs={12}>
            <FormControl component="fieldset">
              <FormLabel component="legend">Notification Frequency</FormLabel>
              <RadioGroup
                row
                name="notificationFrequency"
                value={formState.notificationFrequency}
                onChange={handleInputChange}
              >
                {NOTIFICATION_FREQUENCIES.map(option => (
                  <FormControlLabel 
                    key={option.value}
                    value={option.value} 
                    control={<Radio />} 
                    label={option.label} 
                  />
                ))}
              </RadioGroup>
            </FormControl>
          </Grid>
          
          {/* Filter Criteria */}
          <Grid item xs={12}>
            <Typography variant="h6" sx={{ mt: 2, mb: 2 }}>
              Filter Criteria
            </Typography>
          </Grid>
          
          {/* Keywords */}
          <Grid item xs={12}>
            <Typography variant="subtitle1">Keywords</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <TextField
                fullWidth
                placeholder="Enter keywords (e.g., 'bridge', 'renovation')"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddKeyword();
                  }
                }}
              />
              <Button 
                variant="contained" 
                sx={{ ml: 2 }}
                onClick={handleAddKeyword}
              >
                Add
              </Button>
            </Box>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {formState.keywords.map(keyword => (
                <Chip 
                  key={keyword}
                  label={keyword}
                  onDelete={() => handleRemoveKeyword(keyword)}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          </Grid>
          
          {/* Locations */}
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth>
              <InputLabel id="locations-label">Locations</InputLabel>
              <Select
                labelId="locations-label"
                id="locations"
                multiple
                value={formState.locations}
                onChange={(e) => handleMultiSelectChange(e, 'locations')}
                input={<OutlinedInput label="Locations" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} />
                    ))}
                  </Box>
                )}
              >
                {LOCATIONS.map((location) => (
                  <MenuItem key={location} value={location}>
                    <Checkbox checked={formState.locations.indexOf(location) > -1} />
                    <ListItemText primary={location} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          {/* Sources */}
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth>
              <InputLabel id="sources-label">Sources</InputLabel>
              <Select
                labelId="sources-label"
                id="sources"
                multiple
                value={formState.sources}
                onChange={(e) => handleMultiSelectChange(e, 'sources')}
                input={<OutlinedInput label="Sources" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} />
                    ))}
                  </Box>
                )}
              >
                {SOURCES.map((source) => (
                  <MenuItem key={source} value={source}>
                    <Checkbox checked={formState.sources.indexOf(source) > -1} />
                    <ListItemText primary={source} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          {/* Value Range */}
          <Grid item xs={12}>
            <Typography variant="subtitle1">Value Range (AUD)</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  id="capitalValueMin"
                  label="Minimum Value"
                  name="capitalValueMin"
                  value={formState.capitalValueMin}
                  onChange={handleInputChange}
                  error={!!errors.capitalValueMin}
                  helperText={errors.capitalValueMin}
                  InputProps={{
                    startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>,
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  id="capitalValueMax"
                  label="Maximum Value"
                  name="capitalValueMax"
                  value={formState.capitalValueMax}
                  onChange={handleInputChange}
                  error={!!errors.capitalValueMax}
                  helperText={errors.capitalValueMax}
                  InputProps={{
                    startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>,
                  }}
                />
              </Grid>
            </Grid>
          </Grid>
          
          {/* Submit Button */}
          <Grid item xs={12}>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              size="large"
              disabled={isSubmitting}
              sx={{ mt: 2, py: 1.5 }}
            >
              {isSubmitting ? 'Subscribing...' : 'Subscribe to Notifications'}
            </Button>
          </Grid>
        </Grid>
      </Box>
      
      {/* Success/Error Feedback */}
      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default SubscriptionForm;
