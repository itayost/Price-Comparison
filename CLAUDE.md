# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Run Commands
- **Python API Server**: `uvicorn api_server:app --reload` (from StoreAPI or price_comparison_server directory)
- **Android App**: `./gradlew build` or `./gradlew test` from PriceComparisonApp2 directory
- **Single Android Test**: `./gradlew :app:testDebugUnitTest --tests "com.example.pricecomparisonapp.TESTNAME"`

## Code Style Guidelines
- **Python**: Use PEP 8, type hints with Pydantic models, handle exceptions with specific error codes
- **Kotlin/Android**: Follow standard Kotlin conventions, use Compose for UI, use ViewModels
- **Error Handling**: Use HTTPException with appropriate status codes in API, try/catch in Kotlin
- **Database**: Use SQLite for structured price data storage, always close connections
- **Naming**: camelCase for Kotlin, snake_case for Python
- **Comments**: Document complex algorithms and public APIs, use docstrings
- **Security**: Never commit API keys, sanitize inputs, use proper auth