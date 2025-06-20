from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
import threading
import schedule
import time
import sys
import os

# Add the project root to sys.path for proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from server module for scheduled scraping
from server import scrape_shufersal, scrape_victory

# Import database initializations
from database.connection import init_db
from routes.auth_routes import router as auth_router
from routes.price_routes import router as price_router
from routes.cart_routes import router as cart_router

# Create the FastAPI application
app = FastAPI(
    title="Champion Cart API", 
    description="API for the Champion Cart price comparison application with improved search and price calculation. <br/> Currently supports Victory & Shufersal!", 
    version="2.0"
)

# Include routers
app.include_router(auth_router)
app.include_router(price_router)
app.include_router(cart_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to the Champion Cart API",
        "version": "2.0",
        "database": "PostgreSQL",
        "improvements": [
            "Migrated to PostgreSQL for better scalability",
            "Improved database performance",
            "Ready for production deployment"
        ]
    }

# Run scheduled scraping on startup
def run_scheduled_tasks():
    scrape_shufersal()
    scrape_victory()
    schedule.every(1).hour.do(scrape_shufersal)
    schedule.every(1).hour.do(scrape_victory)

    while True:
        schedule.run_pending()
        time.sleep(1)

# Start scheduled scraping in a separate thread
def start_scheduled_scraping():
    threading.Thread(target=run_scheduled_tasks, daemon=True).start()

# Call start_scheduled_scraping when the app starts
@app.on_event("startup")
def startup_event():
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    start_scheduled_scraping()

# Run the API server with:
# uvicorn api_server:app --host 0.0.0.0 --reload
#
# IMPORTANT: The --host 0.0.0.0 flag is required to make the server accessible
# from mobile devices on the same network. Without it, the server will only be
# accessible from the local machine (localhost).
