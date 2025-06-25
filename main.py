# price_comparison_server/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

# Initialize database
from database.connection import init_db

# Import routers
from routes.cart_routes import router as cart_router
from routes.auth_routes import router as auth_router
from routes.saved_carts_routes import router as saved_carts_router
from routes.system_routes import router as system_router
from routes.product_routes import router as product_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    try:
        if os.getenv("TESTING") != "true":  # Skip for tests
            init_db()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield  # Server runs

    # Shutdown (if needed)
    logger.info("Shutting down...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Price Comparison API",
    description="Compare grocery prices across Israeli supermarket chains",
    version="2.0.0",
    lifespan=lifespan  # Use lifespan instead of on_event
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cart_router)
app.include_router(auth_router)
app.include_router(saved_carts_router)
app.include_router(system_router)
app.include_router(product_router)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Price Comparison API",
        "version": "2.0.0",
        "endpoints": {
            "cart": "/api/cart",
            "auth": "/api/auth",
            "products": "/api/products",
            "saved-carts": "/api/saved-carts",
            "system": "/api/system",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
