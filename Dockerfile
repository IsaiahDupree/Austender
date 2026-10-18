# Use official Python image as base
FROM python:3.10-slim as backend

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY api/ api/
COPY database/ database/
COPY scrapers/ scrapers/
COPY utils/ utils/
COPY scripts/ scripts/
COPY config/ config/
COPY logs/ logs/
COPY main.py .
COPY .env .

# Set up the database
RUN python main.py --init-db

# Build frontend
FROM node:16 as frontend-build

WORKDIR /app

# Copy frontend files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the frontend code
COPY frontend/ ./

# Build frontend
RUN npm run build

# Final image
FROM python:3.10-slim

WORKDIR /app

# Copy backend from backend stage
COPY --from=backend /app /app
COPY --from=backend /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Copy built frontend from frontend-build stage
COPY --from=frontend-build /app/build /app/frontend/build

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "main.py", "--api-only"]
