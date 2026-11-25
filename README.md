# SpendAI — AI-Based Expense Tracker 

A Flask + MongoDB personal finance mini-project with an ML/NLP component.

## Features
- Responsive finance dashboard
- Income and expense tracking
- Natural-language transaction parsing
- Automatic expense category classification
- Monthly budget tracking
- Transaction filters
- AI insights
- Category and monthly reports
- CSV export
- Mobile navigation

## AI implementation
The classifier uses TF-IDF text features and Logistic Regression. The natural-language parser detects an amount, basic date terms, common payment methods, and a predicted expense category.

Example: `₹450 dinner at Domino's yesterday using UPI`

## Requirements
- Python 3.10+
- MongoDB

## Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set your own values.
5. Start MongoDB.
6. Run: `python app.py`
7. Open `http://127.0.0.1:5000`

## Demo flow
Register → set budget → add income → add expenses → review Dashboard, AI Insights and Reports → export CSV.

## Note
Educational mini-project, not a production financial application. Production use would require CSRF protection, stronger validation, rate limiting, secure session configuration, HTTPS, model evaluation, and improved natural-language parsing.
