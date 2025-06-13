#!/bin/bash
# Load Oracle environment variables
export $(cat .env.oracle | grep -v '^#' | xargs)

# Set TNS_ADMIN to wallet directory
export TNS_ADMIN=./wallet

echo "Starting server with Oracle database..."
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
