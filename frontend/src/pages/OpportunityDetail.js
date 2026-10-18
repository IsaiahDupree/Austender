import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Box, 
  Typography, 
  Paper, 
  Grid, 
  Chip,
  Button,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Link,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Tab,
  Tabs
} from '@mui/material';
import dayjs from 'dayjs';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BusinessIcon from '@mui/icons-material/Business';
import DescriptionIcon from '@mui/icons-material/Description';
import PersonIcon from '@mui/icons-material/Person';
import EmailIcon from '@mui/icons-material/Email';
import PhoneIcon from '@mui/icons-material/Phone';
import AttachFileIcon from '@mui/icons-material/AttachFile';

const OpportunityDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    const fetchOpportunity = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await axios.get(`/opportunities/${id}`);
        setOpportunity(response.data);
      } catch (err) {
        console.error('Error fetching opportunity details:', err);
        setError('Failed to fetch opportunity details. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchOpportunity();
  }, [id]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return dayjs(dateString).format('DD MMMM YYYY');
  };

  const formatCurrency = (value, currency = 'AUD') => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-AU', { 
      style: 'currency', 
      currency: currency 
    }).format(value);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ py: 2 }}>
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
        <Button 
          startIcon={<ArrowBackIcon />} 
          onClick={() => navigate('/opportunities')}
        >
          Back to Opportunities
        </Button>
      </Box>
    );
  }

  if (!opportunity) {
    return (
      <Box sx={{ py: 2 }}>
        <Alert severity="warning" sx={{ mb: 3 }}>Opportunity not found.</Alert>
        <Button 
          startIcon={<ArrowBackIcon />} 
          onClick={() => navigate('/opportunities')}
        >
          Back to Opportunities
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, py: 2 }}>
      <Button 
        startIcon={<ArrowBackIcon />} 
        onClick={() => navigate('/opportunities')}
        sx={{ mb: 2 }}
      >
        Back to Opportunities
      </Button>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1">
            {opportunity.title}
          </Typography>
          <Chip 
            label={opportunity.source} 
            color="primary" 
            variant="outlined" 
          />
        </Box>
        
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
          {opportunity.category && (
            <Chip label={opportunity.category} color="secondary" size="small" />
          )}
          {opportunity.subcategory && (
            <Chip label={opportunity.subcategory} variant="outlined" size="small" />
          )}
          {opportunity.tags && opportunity.tags.split(',').map((tag, index) => (
            <Chip key={index} label={tag.trim()} variant="outlined" size="small" />
          ))}
        </Box>
        
        <Divider sx={{ mb: 3 }} />
        
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
          <Tab label="Overview" />
          <Tab label="Details" />
          {opportunity.attachments && opportunity.attachments.length > 0 && (
            <Tab label="Attachments" />
          )}
        </Tabs>
        
        {tabValue === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Key Information
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <BusinessIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Reference ID" 
                        secondary={opportunity.reference_id || 'N/A'} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <CalendarTodayIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Published Date" 
                        secondary={formatDate(opportunity.publish_date)} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <CalendarTodayIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Closing Date" 
                        secondary={formatDate(opportunity.closing_date)} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <AttachMoneyIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Capital Value" 
                        secondary={formatCurrency(opportunity.capital_value, opportunity.capital_value_currency)} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <LocationOnIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Location" 
                        secondary={opportunity.location || 'N/A'} 
                      />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Contact Information
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <PersonIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Contact Name" 
                        secondary={opportunity.contact_name || 'N/A'} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <EmailIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Email" 
                        secondary={
                          opportunity.contact_email ? (
                            <Link href={`mailto:${opportunity.contact_email}`}>
                              {opportunity.contact_email}
                            </Link>
                          ) : 'N/A'
                        } 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <PhoneIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Phone" 
                        secondary={opportunity.contact_phone || 'N/A'} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <BusinessIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Procurement Method" 
                        secondary={opportunity.procurement_method || 'N/A'} 
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <BusinessIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Panel Arrangement" 
                        secondary={opportunity.panel_name || (opportunity.panel_arrangement ? 'Yes' : 'No')} 
                      />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Description
                  </Typography>
                  <Typography variant="body1" component="div" sx={{ whiteSpace: 'pre-line' }}>
                    {opportunity.description || 'No description available.'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
        
        {tabValue === 1 && (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Timing Information
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2">Published Date:</Typography>
                      <Typography variant="body1">{formatDate(opportunity.publish_date)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2">Closing Date:</Typography>
                      <Typography variant="body1">{formatDate(opportunity.closing_date)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2">Start Date:</Typography>
                      <Typography variant="body1">{formatDate(opportunity.start_date)}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="subtitle2">Duration:</Typography>
                      <Typography variant="body1">{opportunity.estimated_duration || 'N/A'}</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Financial Information
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2">Capital Value:</Typography>
                      <Typography variant="body1">
                        {formatCurrency(opportunity.capital_value, opportunity.capital_value_currency)}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2">Currency:</Typography>
                      <Typography variant="body1">{opportunity.capital_value_currency || 'AUD'}</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Location Information
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2">Location:</Typography>
                      <Typography variant="body1">{opportunity.location || 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2">Region:</Typography>
                      <Typography variant="body1">{opportunity.region || 'N/A'}</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Additional Information
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2">Created:</Typography>
                      <Typography variant="body1">
                        {opportunity.created_at ? dayjs(opportunity.created_at).format('DD MMMM YYYY HH:mm') : 'N/A'}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2">Last Updated:</Typography>
                      <Typography variant="body1">
                        {opportunity.updated_at ? dayjs(opportunity.updated_at).format('DD MMMM YYYY HH:mm') : 'N/A'}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
        
        {tabValue === 2 && opportunity.attachments && (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Attachments
                  </Typography>
                  <List>
                    {opportunity.attachments.length > 0 ? (
                      opportunity.attachments.map((attachment, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <AttachFileIcon />
                          </ListItemIcon>
                          <ListItemText 
                            primary={
                              <Link href={attachment.url} target="_blank" rel="noopener noreferrer">
                                {attachment.name || `Attachment ${index + 1}`}
                              </Link>
                            }
                            secondary={attachment.description || 'No description provided'}
                          />
                        </ListItem>
                      ))
                    ) : (
                      <ListItem>
                        <ListItemText primary="No attachments available." />
                      </ListItem>
                    )}
                  </List>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
        
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
          <Button 
            variant="outlined" 
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/opportunities')}
          >
            Back to Opportunities
          </Button>
          
          {opportunity.url && (
            <Button 
              variant="contained" 
              color="primary"
              component={Link}
              href={opportunity.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              View Source
            </Button>
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default OpportunityDetail;
