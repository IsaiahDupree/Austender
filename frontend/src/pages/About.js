import React from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import WebIcon from '@mui/icons-material/Web';
import BarChartIcon from '@mui/icons-material/BarChart';
import NotificationsIcon from '@mui/icons-material/Notifications';
import StorageIcon from '@mui/icons-material/Storage';
import SearchIcon from '@mui/icons-material/Search';
import UpdateIcon from '@mui/icons-material/Update';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import SecurityIcon from '@mui/icons-material/Security';

const About = () => {
  return (
    <Box sx={{ flexGrow: 1, py: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        About This Platform
      </Typography>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Government Construction Opportunities
        </Typography>
        <Typography variant="body1" paragraph>
          This platform provides a comprehensive solution for tracking and analyzing government construction opportunities from multiple sources, with a primary focus on Austender.
        </Typography>
        <Typography variant="body1" paragraph>
          Our automated system collects data from Austender, ANI, ICN, and SAM, providing you with over 300 opportunities in a searchable database with advanced filtering capabilities.
        </Typography>
        <Typography variant="body1">
          The platform is designed for construction companies, developers, and contractors who need to stay informed about government construction opportunities in a timely and efficient manner.
        </Typography>
      </Paper>
      
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Key Features
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <WebIcon color="primary" sx={{ fontSize: 28, mr: 1 }} />
                <Typography variant="h6">
                  Professional-Grade Website
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Our platform features a modern, responsive design that works on all devices. The user interface is intuitive and easy to navigate, allowing you to quickly find the information you need.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <AutorenewIcon color="primary" sx={{ fontSize: 28, mr: 1 }} />
                <Typography variant="h6">
                  Automated Data Collection
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Our system automatically scrapes government websites to collect the latest construction opportunities. This ensures that you always have access to the most current information without manual effort.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <SearchIcon color="primary" sx={{ fontSize: 28, mr: 1 }} />
                <Typography variant="h6">
                  Advanced Search and Filtering
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Our platform includes powerful search functionality that allows you to filter opportunities by source, category, location, value, and dates. This makes it easy to find relevant opportunities that match your specific criteria.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <BarChartIcon color="primary" sx={{ fontSize: 28, mr: 1 }} />
                <Typography variant="h6">
                  Detailed Analytics
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Our platform provides comprehensive analytics and statistics to help you understand market trends, opportunity distribution, and value analysis. This data-driven approach gives you valuable insights for strategic decision-making.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <NotificationsIcon color="primary" sx={{ fontSize: 28, mr: 1 }} />
                <Typography variant="h6">
                  Email Notifications
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Our platform sends automated email notifications for new opportunities, ensuring that you never miss out on potential business. These notifications can be customized to match your specific interests and requirements.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <UpdateIcon color="primary" sx={{ fontSize: 28, mr: 1 }} />
                <Typography variant="h6">
                  Regular Updates
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Our platform is updated twice a month to ensure that all information is current and accurate. The system automatically maintains and refreshes the database to provide you with the most up-to-date opportunities.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Technical Details
      </Typography>
      
      <Paper sx={{ p: 3 }}>
        <List>
          <ListItem>
            <ListItemIcon>
              <StorageIcon color="primary" />
            </ListItemIcon>
            <ListItemText 
              primary="Data Sources" 
              secondary="Our platform collects data from multiple government sources including Austender (primary), ANI, ICN, and SAM. This comprehensive approach ensures that you have access to a wide range of opportunities."
            />
          </ListItem>
          <Divider component="li" />
          <ListItem>
            <ListItemIcon>
              <WebIcon color="primary" />
            </ListItemIcon>
            <ListItemText 
              primary="Web Technology" 
              secondary="The platform is built using modern web technologies including React for the frontend, FastAPI for the backend, and SQL database for storage. This stack ensures high performance, reliability, and scalability."
            />
          </ListItem>
          <Divider component="li" />
          <ListItem>
            <ListItemIcon>
              <SecurityIcon color="primary" />
            </ListItemIcon>
            <ListItemText 
              primary="Data Analysis" 
              secondary="Our platform leverages advanced AI technologies including OpenAI, Perplexity, and Firecrawl to analyze opportunity documents, extract key information, and provide insights that would be difficult to obtain manually."
            />
          </ListItem>
        </List>
      </Paper>
      
      <Box sx={{ mt: 4, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          Contact Information
        </Typography>
        <Typography variant="body1">
          For more information or support, please contact us at:
        </Typography>
        <Typography variant="body1" sx={{ mt: 1 }}>
          Email: support@constructionopportunities.com
        </Typography>
        <Typography variant="body1">
          Phone: +61 123 456 789
        </Typography>
      </Box>
    </Box>
  );
};

export default About;
