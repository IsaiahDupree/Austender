# Government Construction Opportunities Tracker

## Project Overview

This platform provides an automated system for tracking government construction opportunities from various sources:

- **Austender** (primary focus) - Australian Government tenders
- **ANI** (Australian National Infrastructure)
- **ICN** (Industry Capability Network)
- **SAM** (System for Award Management - US Government)

The system uses AI-powered analysis (OpenAI, Perplexity, and Firecrawl) to extract and understand detailed information from opportunity documents and provides a modern web interface for searching, filtering, and analyzing opportunities.

## Key Features

- **Automated Data Collection**: Regular scraping of government websites for new opportunities
- **Advanced Search & Filtering**: Filter by source, category, location, value range, and dates
- **Detailed Information**: Access market timing, capital value, scope, source links, and more
- **Email Notifications**: Automated alerts about new relevant opportunities
- **Data Analysis**: AI-powered document analysis with OpenAI, Perplexity, and Firecrawl
- **Interactive Dashboard**: Visual statistics and opportunity metrics
- **Responsive Design**: Mobile-friendly interface that works across all devices

## Project Structure

- `scrapers/` - Web scraping modules for different opportunity sources
- `database/` - Database models and connection logic
- `api/` - FastAPI endpoints for the web application
- `frontend/` - React-based web interface
- `utils/` - Utility functions including AI document analysis
- `config/` - Configuration files and environment settings
- `scripts/` - Automation and maintenance scripts
- `tests/` - Unit and integration tests
- `logs/` - Application logs

## Requirements

- Python 3.10+
- Node.js 16+
- npm or yarn
- Docker and Docker Compose (optional for containerized deployment)
- OpenAI API key (for document analysis)
- Perplexity API key (for research capabilities)
- Firecrawl API key (for web crawling)
- SMTP server (for email notifications)

## Setup Instructions

### Option 1: Automated Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd Austender
   ```

2. Create a `.env` file based on `.env.example` and add your API keys

3. Run the setup script:

   ```bash
   python setup.py
   ```

### Option 2: Manual Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd Austender
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:

   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. Create a `.env` file based on `.env.example` and add your API keys:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. Initialize the database:

   ```bash
   python main.py --init-db
   ```

### Option 3: Docker Deployment

1. Clone the repository and create `.env` file as above

2. Build and start containers:

   ```bash
   docker-compose up -d
   ```

## Running the Application

### Development Mode

1. Start the backend API server:

   ```bash
   python main.py --api-only
   ```

2. Start the scheduler (in a new terminal):

   ```bash
   python main.py --scheduler-only
   ```

3. Start the frontend development server (in a new terminal):

   ```bash
   cd frontend
   npm start
   ```

4. Access the application at [http://localhost:3000](http://localhost:3000)

### Production Mode

Use the deployment script:

```bash
python scripts/deploy.py
```

Or with Docker:

```bash
docker-compose up -d
```

## Running Tests

Execute the test suite:

```bash
pytest
```

Or run specific tests:

```bash
pytest tests/test_austender_scraper.py
pytest tests/test_document_analyzer.py
```

## Manual Operations

### Run Scraper On-Demand

```bash
python main.py --run-scraper
```

### Initialize Database

```bash
python main.py --init-db
```

## API Documentation

When the API server is running, API documentation is available at:

- [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

## Contributing

Please follow these guidelines when contributing to the project:

- Create a branch for new features/fixes
- Write tests for new functionality
- Ensure code passes all existing tests
- Follow the established coding style
- Submit a pull request for review

## License

[License information will be added here]
