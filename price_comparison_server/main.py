# price_comparison_server/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import routers
from routes.cart_routes import router as cart_router
from routes.auth_routes import router as auth_router
from routes.saved_carts_routes import router as saved_carts_router
from routes.system_routes import router as system_router
from routes.product_routes import router as product_router
# from routes.auth_routes import router as auth_router  # To be implemented
# from routes.saved_carts_routes import router as saved_carts_router  # To be implemented

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Price Comparison API",
    description="Compare grocery prices across Israeli supermarket chains",
    version="2.0.0"
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
# app.include_router(auth_router)  # Uncomment when implemented
# app.include_router(saved_carts_router)  # Uncomment when implemented

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Price Comparison API",
        "version": "2.0.0",
        "endpoints": {
            "cart": "/api/cart",
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
