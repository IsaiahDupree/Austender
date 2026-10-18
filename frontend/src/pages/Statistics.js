import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Box, 
  Typography, 
  Paper, 
  Grid, 
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tab
} from '@mui/material';
import { 
  Chart as ChartJS, 
  ArcElement, 
  Tooltip, 
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  PointElement,
  LineElement,
  TimeScale
} from 'chart.js';
import { Pie, Bar, Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import dayjs from 'dayjs';

// Register ChartJS components
ChartJS.register(
  ArcElement, 
  Tooltip, 
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  PointElement,
  LineElement,
  TimeScale
);

const Statistics = () => {
  const [stats, setStats] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch statistics and opportunities in parallel
        const [statsRes, opportunitiesRes] = await Promise.all([
          axios.get('/stats'),
          axios.get('/opportunities', { 
            params: { limit: 100 } 
          })
        ]);
        
        setStats(statsRes.data);
        setOpportunities(opportunitiesRes.data);
      } catch (err) {
        console.error('Error fetching statistics data:', err);
        setError('Failed to load statistics. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // Helper function to format currency
  const formatCurrency = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-AU', { 
      style: 'currency', 
      currency: 'AUD',
      maximumFractionDigits: 0
    }).format(value);
  };
  
  // Prepare source chart data
  const getSourceChartData = () => {
    if (!stats || !stats.by_source) return null;
    
    const labels = Object.keys(stats.by_source);
    const data = labels.map(source => stats.by_source[source]);
    
    return {
      labels,
      datasets: [
        {
          label: 'Number of Opportunities',
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
  
  // Prepare category chart data
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
  
  // Prepare location chart data
  const getLocationChartData = () => {
    if (!stats || !stats.by_location) return null;
    
    // Sort locations by count and take top 10
    const sortedLocations = Object.entries(stats.by_location)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
    
    const labels = sortedLocations.map(([location]) => location);
    const data = sortedLocations.map(([, count]) => count);
    
    return {
      labels,
      datasets: [
        {
          label: 'Number of Opportunities',
          data,
          backgroundColor: '#4caf50',
        },
      ],
    };
  };
  
  // Prepare timeline chart data
  const getTimelineChartData = () => {
    if (!opportunities || opportunities.length === 0) return null;
    
    // Prepare data by publish date
    const publishDateMap = new Map();
    
    opportunities.forEach(opp => {
      if (opp.publish_date) {
        const date = dayjs(opp.publish_date).format('YYYY-MM-DD');
        publishDateMap.set(date, (publishDateMap.get(date) || 0) + 1);
      }
    });
    
    // Sort dates
    const sortedDates = Array.from(publishDateMap.keys()).sort();
    
    return {
      labels: sortedDates,
      datasets: [
        {
          label: 'New Opportunities',
          data: sortedDates.map(date => publishDateMap.get(date)),
          borderColor: '#1976d2',
          backgroundColor: 'rgba(25, 118, 210, 0.2)',
          tension: 0.1,
          fill: true,
        },
      ],
    };
  };
  
  // Prepare value distribution chart
  const getValueDistributionChart = () => {
    if (!opportunities || opportunities.length === 0) return null;
    
    // Define value ranges
    const ranges = [
      { min: 0, max: 100000, label: '0-100K' },
      { min: 100000, max: 500000, label: '100K-500K' },
      { min: 500000, max: 1000000, label: '500K-1M' },
      { min: 1000000, max: 5000000, label: '1M-5M' },
      { min: 5000000, max: 10000000, label: '5M-10M' },
      { min: 10000000, max: Infinity, label: '10M+' }
    ];
    
    // Count opportunities in each range
    const rangeCounts = ranges.map(range => ({
      ...range,
      count: opportunities.filter(opp => 
        opp.capital_value !== null && 
        opp.capital_value >= range.min && 
        opp.capital_value < range.max
      ).length
    }));
    
    return {
      labels: rangeCounts.map(range => range.label),
      datasets: [
        {
          label: 'Number of Opportunities',
          data: rangeCounts.map(range => range.count),
          backgroundColor: '#ff9800',
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
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  };
  
  const lineOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Opportunities Over Time',
      },
    },
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'day'
        },
        title: {
          display: true,
          text: 'Date'
        }
      },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Count'
        }
      }
    }
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
        Statistics and Analytics
      </Typography>
      
      <Paper sx={{ mb: 3 }}>
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange} 
          indicatorColor="primary"
          textColor="primary"
          centered
        >
          <Tab label="Overview" />
          <Tab label="Source Analysis" />
          <Tab label="Category Analysis" />
          <Tab label="Value Analysis" />
          <Tab label="Timeline" />
        </Tabs>
      </Paper>
      
      {tabValue === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Summary Statistics
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      <TableCell align="right">Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Total Opportunities</TableCell>
                      <TableCell align="right">{stats?.total_opportunities || 0}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Number of Sources</TableCell>
                      <TableCell align="right">{stats ? Object.keys(stats.by_source).length : 0}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Number of Categories</TableCell>
                      <TableCell align="right">{stats ? Object.keys(stats.by_category || {}).length : 0}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Number of Locations</TableCell>
                      <TableCell align="right">{stats ? Object.keys(stats.by_location || {}).length : 0}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Average Value (Austender)</TableCell>
                      <TableCell align="right">
                        {stats?.avg_values?.Austender ? formatCurrency(stats.avg_values.Austender) : 'N/A'}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
          
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
                Value Distribution
              </Typography>
              <Box sx={{ height: 300 }}>
                {getValueDistributionChart() ? (
                  <Bar options={barOptions} data={getValueDistributionChart()} />
                ) : (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography color="text.secondary">
                      No value data available
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}
      
      {tabValue === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Opportunities by Source
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Box sx={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    {getSourceChartData() ? (
                      <Pie data={getSourceChartData()} />
                    ) : (
                      <Typography color="text.secondary">
                        No source data available
                      </Typography>
                    )}
                  </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Source</TableCell>
                          <TableCell align="right">Count</TableCell>
                          <TableCell align="right">Percentage</TableCell>
                          <TableCell align="right">Avg. Value</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {stats && stats.by_source && Object.entries(stats.by_source).map(([source, count]) => (
                          <TableRow key={source}>
                            <TableCell>{source}</TableCell>
                            <TableCell align="right">{count}</TableCell>
                            <TableCell align="right">
                              {((count / stats.total_opportunities) * 100).toFixed(1)}%
                            </TableCell>
                            <TableCell align="right">
                              {stats.avg_values && stats.avg_values[source] ? 
                                formatCurrency(stats.avg_values[source]) : 'N/A'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}
      
      {tabValue === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Top Categories
              </Typography>
              <Box sx={{ height: 400 }}>
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
          
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Top Locations
              </Typography>
              <Box sx={{ height: 400 }}>
                {getLocationChartData() ? (
                  <Bar options={barOptions} data={getLocationChartData()} />
                ) : (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography color="text.secondary">
                      No location data available
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}
      
      {tabValue === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Value Distribution
              </Typography>
              <Box sx={{ height: 400 }}>
                {getValueDistributionChart() ? (
                  <Bar options={barOptions} data={getValueDistributionChart()} />
                ) : (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography color="text.secondary">
                      No value data available
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>
          
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Value Statistics
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      <TableCell align="right">Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stats && stats.avg_values && Object.entries(stats.avg_values).map(([source, avgValue]) => (
                      <TableRow key={source}>
                        <TableCell>Average Value ({source})</TableCell>
                        <TableCell align="right">{formatCurrency(avgValue)}</TableCell>
                      </TableRow>
                    ))}
                    <TableRow>
                      <TableCell>Lowest Value</TableCell>
                      <TableCell align="right">
                        {opportunities.length > 0 ? 
                          formatCurrency(Math.min(...opportunities
                            .filter(opp => opp.capital_value !== null && opp.capital_value > 0)
                            .map(opp => opp.capital_value))) : 'N/A'}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Highest Value</TableCell>
                      <TableCell align="right">
                        {opportunities.length > 0 ? 
                          formatCurrency(Math.max(...opportunities
                            .filter(opp => opp.capital_value !== null)
                            .map(opp => opp.capital_value))) : 'N/A'}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      )}
      
      {tabValue === 4 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Opportunities Timeline
              </Typography>
              <Box sx={{ height: 400 }}>
                {getTimelineChartData() ? (
                  <Line options={lineOptions} data={getTimelineChartData()} />
                ) : (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography color="text.secondary">
                      Not enough timeline data available
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default Statistics;
