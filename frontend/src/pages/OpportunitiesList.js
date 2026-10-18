import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Box, 
  Typography, 
  Paper, 
  TextField, 
  Grid, 
  Button, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem,
  Chip,
  Card,
  CardContent,
  CardActions,
  Pagination,
  Stack,
  CircularProgress,
  Snackbar,
  Alert
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import FolderIcon from '@mui/icons-material/Folder';
import BusinessIcon from '@mui/icons-material/Business';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import PlaceIcon from '@mui/icons-material/Place';

// API URL - replace with your actual API URL in production
const API_URL = '/opportunities';

const OpportunitiesList = () => {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize] = useState(12);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [minValue, setMinValue] = useState('');
  const [maxValue, setMaxValue] = useState('');
  const [publishedAfter, setPublishedAfter] = useState(null);
  const [closingAfter, setClosingAfter] = useState(null);
  
  // Options for filters
  const [sources, setSources] = useState([]);
  const [categories, setCategories] = useState([]);
  const [locations, setLocations] = useState([]);
  
  // Load filter options on component mount
  useEffect(() => {
    const fetchFilterOptions = async () => {
      try {
        const [sourcesRes, categoriesRes, locationsRes] = await Promise.all([
          axios.get('/sources'),
          axios.get('/categories'),
          axios.get('/locations')
        ]);
        
        setSources(sourcesRes.data.sources || []);
        setCategories(categoriesRes.data.categories || []);
        setLocations(locationsRes.data.locations || []);
      } catch (err) {
        console.error('Error fetching filter options:', err);
      }
    };
    
    fetchFilterOptions();
  }, []);
  
  // Load opportunities with filters
  useEffect(() => {
    const fetchOpportunities = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const params = {
          skip: (page - 1) * pageSize,
          limit: pageSize,
        };
        
        // Add filters if they exist
        if (searchTerm) params.search = searchTerm;
        if (selectedSource) params.source = selectedSource;
        if (selectedCategory) params.category = selectedCategory;
        if (selectedLocation) params.location = selectedLocation;
        if (minValue) params.min_value = minValue;
        if (maxValue) params.max_value = maxValue;
        if (publishedAfter) params.published_after = dayjs(publishedAfter).format('YYYY-MM-DD');
        if (closingAfter) params.closing_after = dayjs(closingAfter).format('YYYY-MM-DD');
        
        const response = await axios.get(API_URL, { params });
        setOpportunities(response.data);
        setTotalCount(response.headers['x-total-count'] || response.data.length);
      } catch (err) {
        console.error('Error fetching opportunities:', err);
        setError('Failed to fetch opportunities. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchOpportunities();
  }, [page, pageSize, searchTerm, selectedSource, selectedCategory, selectedLocation, 
      minValue, maxValue, publishedAfter, closingAfter]);
  
  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1); // Reset to first page when searching
  };
  
  const handleReset = () => {
    setSearchTerm('');
    setSelectedSource('');
    setSelectedCategory('');
    setSelectedLocation('');
    setMinValue('');
    setMaxValue('');
    setPublishedAfter(null);
    setClosingAfter(null);
    setPage(1);
  };
  
  const handlePageChange = (event, newPage) => {
    setPage(newPage);
  };
  
  const handleOpportunityClick = (id) => {
    navigate(`/opportunities/${id}`);
  };
  
  // Format currency
  const formatCurrency = (value, currency = 'AUD') => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-AU', { 
      style: 'currency', 
      currency: currency 
    }).format(value);
  };
  
  return (
    <Box sx={{ flexGrow: 1, py: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Construction Opportunities
      </Typography>
      
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box component="form" onSubmit={handleSearch} noValidate>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={4} lg={3}>
              <TextField
                fullWidth
                label="Search Opportunities"
                variant="outlined"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  endAdornment: <SearchIcon color="action" />
                }}
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={4} lg={3}>
              <FormControl fullWidth variant="outlined">
                <InputLabel>Source</InputLabel>
                <Select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  label="Source"
                >
                  <MenuItem value="">All Sources</MenuItem>
                  {sources.map((source) => (
                    <MenuItem key={source} value={source}>{source}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={12} md={4} lg={6}>
              <Stack direction="row" spacing={2}>
                <Button 
                  variant="contained" 
                  type="submit"
                  startIcon={<SearchIcon />}
                >
                  Search
                </Button>
                <Button 
                  variant="outlined" 
                  onClick={handleReset}
                >
                  Reset
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setShowFilters(!showFilters)}
                  startIcon={<FilterListIcon />}
                >
                  {showFilters ? 'Hide Filters' : 'More Filters'}
                </Button>
              </Stack>
            </Grid>
            
            {showFilters && (
              <>
                <Grid item xs={12} sm={6} md={4} lg={3}>
                  <FormControl fullWidth variant="outlined">
                    <InputLabel>Category</InputLabel>
                    <Select
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                      label="Category"
                    >
                      <MenuItem value="">All Categories</MenuItem>
                      {categories.map((category) => (
                        <MenuItem key={category} value={category}>{category}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} sm={6} md={4} lg={3}>
                  <FormControl fullWidth variant="outlined">
                    <InputLabel>Location</InputLabel>
                    <Select
                      value={selectedLocation}
                      onChange={(e) => setSelectedLocation(e.target.value)}
                      label="Location"
                    >
                      <MenuItem value="">All Locations</MenuItem>
                      {locations.map((location) => (
                        <MenuItem key={location} value={location}>{location}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} sm={6} md={4} lg={3}>
                  <TextField
                    fullWidth
                    label="Min Value (AUD)"
                    variant="outlined"
                    type="number"
                    value={minValue}
                    onChange={(e) => setMinValue(e.target.value)}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4} lg={3}>
                  <TextField
                    fullWidth
                    label="Max Value (AUD)"
                    variant="outlined"
                    type="number"
                    value={maxValue}
                    onChange={(e) => setMaxValue(e.target.value)}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4} lg={3}>
                  <DatePicker
                    label="Published After"
                    value={publishedAfter}
                    onChange={(newDate) => setPublishedAfter(newDate)}
                    slotProps={{ textField: { fullWidth: true, variant: 'outlined' } }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4} lg={3}>
                  <DatePicker
                    label="Closing After"
                    value={closingAfter}
                    onChange={(newDate) => setClosingAfter(newDate)}
                    slotProps={{ textField: { fullWidth: true, variant: 'outlined' } }}
                  />
                </Grid>
              </>
            )}
          </Grid>
        </Box>
      </Paper>
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
      ) : opportunities.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>No opportunities found matching your criteria.</Alert>
      ) : (
        <>
          <Grid container spacing={3}>
            {opportunities.map((opportunity) => (
              <Grid item xs={12} sm={6} md={4} key={opportunity.id}>
                <Card 
                  sx={{ 
                    height: '100%', 
                    display: 'flex', 
                    flexDirection: 'column',
                    '&:hover': {
                      boxShadow: 6,
                      cursor: 'pointer'
                    }
                  }}
                  onClick={() => handleOpportunityClick(opportunity.id)}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography gutterBottom variant="h6" component="div" noWrap>
                      {opportunity.title}
                    </Typography>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <FolderIcon fontSize="small" color="action" sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        ID: {opportunity.reference_id || 'N/A'}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <BusinessIcon fontSize="small" color="action" sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Source: {opportunity.source}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <CalendarTodayIcon fontSize="small" color="action" sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Closing: {opportunity.closing_date ? 
                          dayjs(opportunity.closing_date).format('DD/MM/YYYY') : 'N/A'}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <AttachMoneyIcon fontSize="small" color="action" sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Value: {formatCurrency(opportunity.capital_value, opportunity.capital_value_currency)}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <PlaceIcon fontSize="small" color="action" sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary" noWrap>
                        Location: {opportunity.location || 'N/A'}
                      </Typography>
                    </Box>
                    
                    {opportunity.category && (
                      <Box sx={{ mt: 2 }}>
                        <Chip label={opportunity.category} size="small" />
                      </Box>
                    )}
                  </CardContent>
                  <CardActions>
                    <Button size="small" color="primary">
                      View Details
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
          
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <Pagination 
              count={Math.ceil(totalCount / pageSize)} 
              page={page} 
              onChange={handlePageChange} 
              color="primary" 
            />
          </Box>
        </>
      )}
      
      <Snackbar 
        open={!!error} 
        autoHideDuration={6000} 
        onClose={() => setError(null)}
      >
        <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default OpportunitiesList;
