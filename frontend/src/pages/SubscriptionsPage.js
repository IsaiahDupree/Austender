import React, { useState, useEffect } from 'react';
import { 
  Container,
  Typography,
  Box,
  Tab,
  Tabs,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  Divider,
  Paper,
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';
import { 
  Edit as EditIcon,
  Delete as DeleteIcon,
  Notifications as NotificationsIcon,
  NotificationsOff as NotificationsOffIcon,
  Money as MoneyIcon,
  LocationOn as LocationIcon,
  Source as SourceIcon,
  Search as SearchIcon
} from '@mui/icons-material';
import axios from 'axios';
import { API_URL } from '../config';
import SubscriptionForm from '../components/SubscriptionForm';

// Tab panel component for the tabbed interface
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`subscription-tabpanel-${index}`}
      aria-labelledby={`subscription-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const SubscriptionsPage = () => {
  // State for tabs
  const [tabValue, setTabValue] = useState(0);
  
  // State for subscriptions
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State for the delete dialog
  const [deleteDialog, setDeleteDialog] = useState({
    open: false,
    subscriptionId: null,
    subscriptionName: ''
  });
  
  // Function to format subscription details for display
  const formatSubscriptionDetails = (subscription) => {
    const filters = subscription.filters || {};
    
    // Format value range
    let valueRange = 'Any';
    if (filters.capital_value) {
      const min = filters.capital_value.min;
      const max = filters.capital_value.max;
      
      if (min !== undefined && max !== undefined) {
        valueRange = `$${min.toLocaleString()} - $${max.toLocaleString()}`;
      } else if (min !== undefined) {
        valueRange = `$${min.toLocaleString()}+`;
      } else if (max !== undefined) {
        valueRange = `Up to $${max.toLocaleString()}`;
      }
    }
    
    return {
      keywords: filters.keywords || [],
      locations: Array.isArray(filters.location) ? filters.location : (filters.location ? [filters.location] : []),
      sources: Array.isArray(filters.source) ? filters.source : (filters.source ? [filters.source] : []),
      valueRange
    };
  };
  
  // Function to load subscriptions
  const loadSubscriptions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`${API_URL}/subscriptions`, {
        headers: {
          'x-api-key': process.env.REACT_APP_API_KEY || 'api-key-placeholder'
        }
      });
      
      setSubscriptions(response.data);
    } catch (err) {
      console.error('Error loading subscriptions:', err);
      setError(err.response?.data?.detail || 'Error loading subscriptions');
    } finally {
      setLoading(false);
    }
  };
  
  // Load subscriptions on component mount
  useEffect(() => {
    loadSubscriptions();
  }, []);
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // Handle subscription toggle (active/inactive)
  const handleToggleSubscription = async (subscriptionId, currentActive) => {
    try {
      await axios.put(
        `${API_URL}/subscriptions/${subscriptionId}`,
        { active: !currentActive },
        {
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': process.env.REACT_APP_API_KEY || 'api-key-placeholder'
          }
        }
      );
      
      // Update local state
      setSubscriptions(subscriptions.map(sub => 
        sub.id === subscriptionId ? { ...sub, active: !currentActive } : sub
      ));
    } catch (err) {
      console.error('Error updating subscription:', err);
      setError(err.response?.data?.detail || 'Error updating subscription');
    }
  };
  
  // Open delete confirmation dialog
  const handleOpenDeleteDialog = (subscription) => {
    setDeleteDialog({
      open: true,
      subscriptionId: subscription.id,
      subscriptionName: subscription.name
    });
  };
  
  // Close delete confirmation dialog
  const handleCloseDeleteDialog = () => {
    setDeleteDialog({
      open: false,
      subscriptionId: null,
      subscriptionName: ''
    });
  };
  
  // Delete a subscription
  const handleDeleteSubscription = async () => {
    if (!deleteDialog.subscriptionId) return;
    
    try {
      await axios.delete(`${API_URL}/subscriptions/${deleteDialog.subscriptionId}`, {
        headers: {
          'x-api-key': process.env.REACT_APP_API_KEY || 'api-key-placeholder'
        }
      });
      
      // Update local state
      setSubscriptions(subscriptions.filter(sub => sub.id !== deleteDialog.subscriptionId));
      
      // Close dialog
      handleCloseDeleteDialog();
    } catch (err) {
      console.error('Error deleting subscription:', err);
      setError(err.response?.data?.detail || 'Error deleting subscription');
      handleCloseDeleteDialog();
    }
  };
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>
        Subscription Management
      </Typography>
      
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        Create and manage your opportunity notification subscriptions
      </Typography>
      
      <Box sx={{ mt: 4 }}>
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="My Subscriptions" />
          <Tab label="Create New Subscription" />
        </Tabs>
      </Box>
      
      <TabPanel value={tabValue} index={0}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : subscriptions.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              No subscriptions found
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Click "Create New Subscription" to set up email notifications for opportunities
            </Typography>
            <Button 
              variant="contained" 
              color="primary" 
              sx={{ mt: 2 }}
              onClick={() => setTabValue(1)}
            >
              Create New Subscription
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {subscriptions.map(subscription => {
              const details = formatSubscriptionDetails(subscription);
              
              return (
                <Grid item xs={12} md={6} key={subscription.id}>
                  <Card 
                    elevation={3}
                    sx={{ 
                      height: '100%', 
                      display: 'flex', 
                      flexDirection: 'column',
                      opacity: subscription.active ? 1 : 0.7
                    }}
                  >
                    <CardContent sx={{ flexGrow: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <Typography variant="h6" gutterBottom>
                          {subscription.name}
                        </Typography>
                        
                        <Chip 
                          label={
                            subscription.notification_frequency === 'immediate' ? 'Immediate' :
                            subscription.notification_frequency === 'daily' ? 'Daily' : 'Weekly'
                          }
                          color={
                            subscription.notification_frequency === 'immediate' ? 'error' :
                            subscription.notification_frequency === 'daily' ? 'primary' : 'secondary'
                          }
                          size="small"
                        />
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {subscription.email}
                      </Typography>
                      
                      <Divider sx={{ my: 2 }} />
                      
                      {/* Keywords */}
                      {details.keywords.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            <SearchIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                            <Typography variant="subtitle2">Keywords</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {details.keywords.map(keyword => (
                              <Chip 
                                key={keyword} 
                                label={keyword} 
                                size="small" 
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        </Box>
                      )}
                      
                      {/* Locations */}
                      {details.locations.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            <LocationIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                            <Typography variant="subtitle2">Locations</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {details.locations.map(location => (
                              <Chip 
                                key={location} 
                                label={location} 
                                size="small" 
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        </Box>
                      )}
                      
                      {/* Sources */}
                      {details.sources.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            <SourceIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                            <Typography variant="subtitle2">Sources</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {details.sources.map(source => (
                              <Chip 
                                key={source} 
                                label={source} 
                                size="small" 
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        </Box>
                      )}
                      
                      {/* Value Range */}
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <MoneyIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                          <Typography variant="subtitle2">Value Range</Typography>
                        </Box>
                        <Typography variant="body2">
                          {details.valueRange}
                        </Typography>
                      </Box>
                      
                      {/* Created/Updated Dates */}
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          Created: {new Date(subscription.created_at).toLocaleDateString()}
                        </Typography>
                        {subscription.last_notification && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Last notification: {new Date(subscription.last_notification).toLocaleDateString()}
                          </Typography>
                        )}
                      </Box>
                    </CardContent>
                    
                    <CardActions sx={{ justifyContent: 'flex-end', p: 2 }}>
                      <Tooltip title={subscription.active ? "Disable notifications" : "Enable notifications"}>
                        <IconButton 
                          onClick={() => handleToggleSubscription(subscription.id, subscription.active)}
                          color={subscription.active ? "primary" : "default"}
                        >
                          {subscription.active ? <NotificationsIcon /> : <NotificationsOffIcon />}
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Edit">
                        <IconButton color="primary">
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Delete">
                        <IconButton 
                          color="error"
                          onClick={() => handleOpenDeleteDialog(subscription)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </CardActions>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        )}
      </TabPanel>
      
      <TabPanel value={tabValue} index={1}>
        <SubscriptionForm onSuccess={() => {
          loadSubscriptions();
          setTabValue(0);
        }} />
      </TabPanel>
      
      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={handleCloseDeleteDialog}
      >
        <DialogTitle>Delete Subscription</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the subscription for "{deleteDialog.subscriptionName}"? 
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDeleteDialog}>Cancel</Button>
          <Button onClick={handleDeleteSubscription} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default SubscriptionsPage;
