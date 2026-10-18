# Tender Scraper Web App

This repository contains the backend API for the Austender & Gov. tender scraper.

## Setup

1. cd backend
2. python -m venv .venv
3. source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
4. pip install -r requirements.txt
5. cp .env.example .env
6. uvicorn app.main:app --reload --port 8000

## Endpoints

- GET  /        => Welcome message  
- GET  /tenders => List tenders  
- GET  /tenders/{id} => Retrieve tender by ID  
- POST /tenders/scrape/austender => Trigger Austender scrape (stub)
