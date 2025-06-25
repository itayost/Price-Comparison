# Price Comparison Server

This server provides APIs to search and compare prices across different supermarket chains in Israel, currently supporting Shufersal and Victory.

## Latest Improvements (v1.1)

The server has been updated with significant improvements to the price comparison functionality:

1. **Enhanced Price Comparison**: Improved algorithm for finding the cheapest cart across stores
2. **Better Product Matching**: More accurate product identification across different chains
3. **Cross-Chain Product Identification**: Properly identifies identical products by item code
4. **Improved Search Results**: Better balance of results between different chains
5. **Savings Calculation**: Shows how much you're saving compared to other stores
6. **More Detailed Response**: Includes item-level price information for better transparency

## Refactoring Improvements (v1.0)

The code has been extensively refactored to improve maintainability and organization:

1. **Modular Structure**: Separated monolithic app into logical modules
2. **Better Abstraction**: Isolated business logic from API routes
3. **Improved Testing**: Added test script to verify functionality
4. **Enhanced Documentation**: Better comments and README file
5. **Cleaner Code**: Smaller functions with single responsibilities
6. **Improved Imports**: Organized imports to follow Python best practices
7. **Enhanced Error Handling**: Added more meaningful error messages

## Project Structure

The project has been organized into a modular structure for better maintainability:

```
price_comparison_server/
├── models/             # Data models
│   ├── __init__.py
│   ├── user_models.py  # Authentication models
│   └── data_models.py  # Price and cart models
│
├── routes/                  # API route definitions
│   ├── __init__.py
│   ├── auth_routes.py           # Authentication endpoints
│   ├── price_routes.py          # Original price comparison endpoints
│   ├── price_routes_new.py      # Refactored price comparison endpoints
│   ├── price_routes_improved.py # Enhanced price comparison endpoints (v1.1)
│   └── cart_routes.py           # Cart management endpoints
│
├── services/           # Business logic
│   ├── __init__.py
│   └── search_service.py  # Product search implementation
│
├── utils/              # Helper utilities
│   ├── __init__.py
│   ├── auth_utils.py   # Authentication helpers
│   ├── db_utils.py     # Database utilities
│   └── product_utils.py # Product data processing
│
├── api_server.py          # Original monolithic server (for backward compatibility)
├── api_server_refactored.py # New modular server with enhanced price comparison (v1.1)
├── server.py           # Scraping utilities
├── users.db            # User and cart database
│
├── shufersal_prices/   # Shufersal price databases
└── victory_prices/     # Victory price databases
```

## Running the Server

The easiest way to run the server is using the provided run script:

```bash
# Activate the virtual environment
cd "/Users/itay/Desktop/Academy/Champion Cart/price_comparison_server"
source venv/bin/activate

# Run the original monolithic server
python run_server.py

# Run the enhanced server with improved price comparison (recommended)
python run_server.py --refactored

# Optionally specify a custom port
python run_server.py --port=8080
```

**Note: For the best price comparison results, we strongly recommend using the refactored server with the `--refactored` flag, which includes our enhanced algorithms for finding the cheapest cart.**

Alternatively, you can use uvicorn directly:

```bash
# Run the original monolithic server
uvicorn api_server:app --host 0.0.0.0 --reload

# Run the refactored server
python -m uvicorn api_server_refactored:app --host 0.0.0.0 --reload
```

Note: The server is configured to listen on all network interfaces (0.0.0.0) to make it accessible from mobile devices on the same network.

The `--host 0.0.0.0` flag is important to make the server accessible from mobile devices on the same network.

## Main Features

1. **Price Comparison**: Search for products and compare prices across Shufersal and Victory
2. **Shopping Cart**: Save and retrieve shopping carts
3. **User Authentication**: Register and login users
4. **Price Per Unit**: Calculate price per unit (g, ml) for better comparison

## API Endpoints

- `/prices/by-item/{city}/{item_name}` - Search for products by name in a specific city
- `/cheapest-cart-all-chains` - Find the cheapest store for a specific cart
- `/savedcarts/{email}` - Retrieve saved carts for a user
- `/savecart` - Save a cart for a user
- `/register` and `/login` - User authentication

## Troubleshooting Tips

1. If search returns no Victory items, check if city name matches exactly
2. For better results, use specific product names rather than generic terms
3. Check database connectivity if errors occur