# Price Comparison Server

A modern REST API server for comparing grocery prices across major supermarket chains in Israel. Built with FastAPI and designed for scalability with support for both SQLite and Oracle Autonomous Database.

## 🚀 Features

### Core Functionality
- **Real-time Price Comparison**: Compare product prices across Shufersal and Victory stores
- **Smart Cart Optimization**: Find the cheapest store for your entire shopping cart
- **Location-Based Search**: Search products and stores by city
- **Barcode Search**: Look up products using exact barcodes
- **Price Statistics**: View min/max/average prices and potential savings

### User Features
- **User Authentication**: JWT-based secure authentication
- **Saved Shopping Carts**: Save and manage multiple shopping lists
- **Cart History**: Track your shopping patterns over time

### Technical Features
- **RESTful API**: Clean, documented API endpoints
- **Database Flexibility**: Supports SQLite (development) and Oracle (production)
- **Automated Data Import**: Scrape and import price data from supermarket websites
- **Comprehensive Testing**: Full test suite with pytest
- **API Documentation**: Auto-generated Swagger/OpenAPI docs at `/docs`

## 📋 Requirements

- Python 3.10+
- SQLite (for development) or Oracle Autonomous Database (for production)
- 4GB+ RAM recommended for data import operations

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd price_comparison_server
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
# Basic Configuration
SECRET_KEY=your-secret-key-here-change-in-production
HOST=0.0.0.0
PORT=8000

# Database Configuration
USE_ORACLE=false  # Set to true for Oracle
DATABASE_URL=sqlite:///./price_comparison.db

# Oracle Configuration (if USE_ORACLE=true)
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your-oracle-password
ORACLE_SERVICE=champdb_low
ORACLE_WALLET_DIR=./wallet
ORACLE_WALLET_PASSWORD=your-wallet-password

# Import Configuration
AUTO_IMPORT=false  # Set to true to import data on startup
IMPORT_LIMIT=0     # Limit files during import (0 = no limit)

# Development
RELOAD=true
SQL_ECHO=false
TESTING=false
```

## 🚀 Quick Start

### Option 1: Run with Automatic Setup
```bash
python main.py
```
The server will automatically:
- Initialize the database
- Create necessary tables
- Start the API server
- (Optional) Import data if `AUTO_IMPORT=true`

### Option 2: Manual Setup
```bash
# 1. Initialize database
python database/connection.py

# 2. Import store data
python scripts/import_chain_data.py --stores-only

# 3. Import price data
python scripts/import_prices.py --limit 10  # Start with 10 files for testing

# 4. Start the server
python main.py
```

## 📚 API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **API Schema**: http://localhost:8000/openapi.json

### Key Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and receive JWT token
- `GET /api/auth/me` - Get current user info

#### Product Search
- `GET /api/products/search?query=חלב&city=תל אביב` - Search products
- `GET /api/products/barcode/{barcode}?city=תל אביב` - Get product by barcode
- `GET /api/products/cities` - List all available cities
- `GET /api/products/chains` - List all supermarket chains

#### Cart Comparison
- `POST /api/cart/compare` - Compare cart prices across all stores
- `GET /api/cart/sample` - Get a sample cart for testing

#### Saved Carts
- `POST /api/saved-carts/save` - Save a shopping cart
- `GET /api/saved-carts/list` - List user's saved carts
- `GET /api/saved-carts/{cart_id}` - Get cart details
- `GET /api/saved-carts/{cart_id}/compare` - Compare saved cart prices

#### System
- `GET /health` - Basic health check
- `GET /api/system/health/detailed` - Detailed system status
- `GET /api/system/statistics` - Database statistics

## 🗄️ Database Schema

The system uses a normalized database design:

### Core Tables
- **chains**: Supermarket chains (Shufersal, Victory)
- **branches**: Store locations with addresses
- **chain_products**: Products specific to each chain
- **branch_prices**: Current prices at each branch

### User Tables
- **users**: Registered users with hashed passwords
- **saved_carts**: User's saved shopping lists

## 🔧 Data Import

The system includes parsers for scraping price data from supermarket websites:

### Import All Data
```bash
# Import both chains
python scripts/import_chain_data.py
python scripts/import_prices.py
```

### Import Specific Chain
```bash
# Import only Shufersal
python scripts/import_chain_data.py --chain shufersal
python scripts/import_prices.py --chain shufersal --limit 5
```

### Import Progress
The import process shows detailed progress:
- Number of stores imported
- Products created/updated
- Prices imported
- Errors encountered

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::TestMainFeatures::test_search_products -v
```

## 🏗️ Project Structure

```
price_comparison_server/
├── database/              # Database models and connection
│   ├── new_models.py     # SQLAlchemy models
│   ├── connection.py     # Database setup
│   └── startup.py        # Initialization logic
│
├── routes/               # API endpoints
│   ├── auth_routes.py    # Authentication
│   ├── product_routes.py # Product search
│   ├── cart_routes.py    # Cart comparison
│   └── saved_carts_routes.py
│
├── services/             # Business logic
│   ├── auth_service.py   # Authentication
│   ├── cart_service.py   # Cart comparison
│   └── product_search_service.py
│
├── parsers/              # Data scrapers
│   ├── base_parser.py    # Abstract parser
│   ├── shufersal_parser.py
│   └── victory_parser.py
│
├── scripts/              # Utility scripts
│   ├── import_chain_data.py
│   └── import_prices.py
│
├── tests/               # Test suite
├── main.py             # Application entry point
└── requirements.txt    # Dependencies
```

## 🚀 Deployment

### Local Network Access
To access from mobile devices on the same network:
```bash
python main.py  # Server runs on 0.0.0.0:8000
```
Access via: `http://YOUR_IP:8000`

### Production Deployment

#### Oracle Cloud Setup
1. Create Oracle Autonomous Database
2. Download wallet files to `./wallet`
3. Configure `.env` with Oracle credentials
4. Set `USE_ORACLE=true`

#### Railway Deployment
The project includes `railway.json` for easy deployment:
```bash
railway up
```

## 🛠️ Development

### Adding a New Supermarket Chain

1. Create a new parser in `parsers/`:
```python
# parsers/newchain_parser.py
from .base_parser import BaseChainParser

class NewChainParser(BaseChainParser):
    def __init__(self):
        super().__init__('newchain', 'chain_code')
        # Implementation...
```

2. Register in `parsers/__init__.py`:
```python
from .newchain_parser import NewChainParser
PARSER_REGISTRY['newchain'] = NewChainParser
```

3. Add to database:
```python
python scripts/import_chain_data.py --chain newchain
```

### API Development
- FastAPI auto-reloads on code changes
- Test new endpoints at `/docs`
- Use Pydantic models for request/response validation

## 🐛 Troubleshooting

### Common Issues

1. **No products found**: Ensure data is imported:
   ```bash
   python scripts/import_chain_data.py
   python scripts/import_prices.py --limit 5
   ```

2. **Database locked (SQLite)**: Ensure only one process accesses the database

3. **City not found**: Check exact spelling:
   ```bash
   curl http://localhost:8000/api/products/cities
   ```

4. **Oracle connection fails**: Verify wallet files in `./wallet` directory

### Logs
- Check console output for detailed error messages
- Set `SQL_ECHO=true` in `.env` for SQL query debugging

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

Copyright (c) 2024 Yarin Manoah, Itay Ostraich

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests before committing
4. Submit a pull request

## 📞 Contact

For questions, suggestions, or issues:
- Yarin Manoah - yarinmanoah1443@gmail.com
- Itay Ostraich - itayost1@gmail.com

You can also:
- Check the `/docs` endpoint for API documentation
- Review test files for usage examples
- Open an issue on the repository

---

**Note**: This system is designed for educational purposes and real-world price comparison in Israel. Price data must be regularly updated for accurate comparisons.
