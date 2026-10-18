import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  Card, 
  CardContent, 
  CardActionArea,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import { 
  Chart as ChartJS, 
  ArcElement, 
  Tooltip, 
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title
} from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';
import AssignmentIcon from '@mui/icons-material/Assignment';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import BusinessIcon from '@mui/icons-material/Business';
import PlaceIcon from '@mui/icons-material/Place';
import dayjs from 'dayjs';

// Register ChartJS components
ChartJS.register(
  ArcElement, 
  Tooltip, 
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title
);

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recentOpportunities, setRecentOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch statistics and recent opportunities in parallel
        const [statsRes, opportunitiesRes] = await Promise.all([
          axios.get('/stats'),
          axios.get('/opportunities', { 
            params: { 
              limit: 5,
              skip: 0
            } 
          })
        ]);
        
        setStats(statsRes.data);
        setRecentOpportunities(opportunitiesRes.data);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);

  // Prepare chart data when stats are available
  const getSourceChartData = () => {
    if (!stats || !stats.by_source) return null;
    
    const labels = Object.keys(stats.by_source);
    const data = labels.map(source => stats.by_source[source]);
    
    return {
      labels,
      datasets: [
        {
          data,
          backgroundColor: [
            '#1976d2',
            '#f44336',
            '#4caf50',
            '#ff9800',
            '#9c27b0',
            '#795548'
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  const getCategoryChartData = () => {
    if (!stats || !stats.by_category) return null;
    
    // Sort categories by count and take top 10
    const sortedCategories = Object.entries(stats.by_category)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
    
    const labels = sortedCategories.map(([category]) => category);
    const data = sortedCategories.map(([, count]) => count);
    
    return {
      labels,
      datasets: [
        {
          label: 'Number of Opportunities',
          data,
          backgroundColor: '#1976d2',
        },
      ],
    };
  };

  const barOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Top Categories',
      },
    },
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
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, py: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* Summary Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Total Opportunities
            </Typography>
            <Typography component="p" variant="h4" sx={{ flexGrow: 1 }}>
              {stats?.total_opportunities || 0}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <AssignmentIcon color="primary" sx={{ mr: 1 }} />
              <Typography color="text.secondary" variant="body2">
                From all sources
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Average Value
            </Typography>
            <Typography component="p" variant="h4" sx={{ flexGrow: 1 }}>
              {stats?.avg_values?.Austender ? 
                `$${(stats.avg_values.Austender).toLocaleString('en-US', {
                  maximumFractionDigits: 0
                })}` : 'N/A'}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <AttachMoneyIcon color="primary" sx={{ mr: 1 }} />
              <Typography color="text.secondary" variant="body2">
                Average Austender value
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Sources
            </Typography>
            <Typography component="p" variant="h4" sx={{ flexGrow: 1 }}>
              {stats ? Object.keys(stats.by_source).length : 0}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <BusinessIcon color="primary" sx={{ mr: 1 }} />
              <Typography color="text.secondary" variant="body2">
                Opportunity sources
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Locations
            </Typography>
            <Typography component="p" variant="h4" sx={{ flexGrow: 1 }}>
              {stats ? Object.keys(stats.by_location || {}).length : 0}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <PlaceIcon color="primary" sx={{ mr: 1 }} />
              <Typography color="text.secondary" variant="body2">
                Different regions
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        {/* Charts */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Opportunities by Source
            </Typography>
            <Box sx={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              {getSourceChartData() ? (
                <Pie data={getSourceChartData()} />
              ) : (
                <Typography color="text.secondary">
                  No source data available
                </Typography>
              )}
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Top Categories
            </Typography>
            <Box sx={{ height: 300 }}>
              {getCategoryChartData() ? (
                <Bar options={barOptions} data={getCategoryChartData()} />
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Typography color="text.secondary">
                    No category data available
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>
        
        {/* Recent Opportunities */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Opportunities
            </Typography>
            {recentOpportunities.length > 0 ? (
              <>
                <List>
                  {recentOpportunities.map((opportunity, index) => (
                    <React.Fragment key={opportunity.id}>
                      <ListItem 
                        button 
                        onClick={() => navigate(`/opportunities/${opportunity.id}`)}
                        sx={{ py: 1.5 }}
                      >
                        <ListItemText
                          primary={opportunity.title}
                          secondary={
                            <React.Fragment>
                              <Typography
                                component="span"
                                variant="body2"
                                color="text.primary"
                                sx={{ display: 'inline' }}
                              >
                                {opportunity.source} - ID: {opportunity.reference_id || 'N/A'}
                              </Typography>
                              {" — "}
                              {opportunity.closing_date ? 
                                `Closing: ${dayjs(opportunity.closing_date).format('DD/MM/YYYY')}` : 'No closing date'}
                              {opportunity.location ? ` — Location: ${opportunity.location}` : ''}
                            </React.Fragment>
                          }
                        />
                      </ListItem>
                      {index < recentOpportunities.length - 1 && <Divider component="li" />}
                    </React.Fragment>
                  ))}
                </List>
                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                  <Button 
                    variant="contained" 
                    color="primary" 
                    onClick={() => navigate('/opportunities')}
                  >
                    View All Opportunities
                  </Button>
                </Box>
              </>
            ) : (
              <Typography color="text.secondary">
                No recent opportunities found
              </Typography>
            )}
          </Paper>
        </Grid>
        
        {/* Quick Actions */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Quick Actions
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardActionArea onClick={() => navigate('/opportunities')}>
                  <CardContent>
                    <AssignmentIcon color="primary" sx={{ fontSize: 36, mb: 1 }} />
                    <Typography variant="h6" gutterBottom>
                      Browse Opportunities
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      View and search all available opportunities
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardActionArea onClick={() => navigate('/statistics')}>
                  <CardContent>
                    <BarChartIcon color="primary" sx={{ fontSize: 36, mb: 1 }} />
                    <Typography variant="h6" gutterBottom>
                      Statistics
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      View detailed statistics and analytics
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
