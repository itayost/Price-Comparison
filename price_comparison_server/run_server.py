#!/usr/bin/env python
"""
Simple wrapper script to run the API server.
This automatically handles imports and module paths.
"""
import sys
import os
import uvicorn

def main():
    """Run the API server."""
    print("Starting Price Comparison API Server...")
    print("Press Ctrl+C to stop the server.")
    
    # Get command line arguments
    host = "0.0.0.0"  # Listen on all network interfaces
    port = 8000
    reload = True
    
    # Extract port number if provided
    for arg in sys.argv:
        if arg.startswith("--port="):
            try:
                port = int(arg.split("=")[1])
            except (IndexError, ValueError):
                print(f"Invalid port format: {arg}. Using default port 8000.")
    
    # Run the improved server file
    app = "api_server:app"
    
    # Run the server
    print(f"Server running at http://{host}:{port}")
    print(f"Documentation available at http://localhost:{port}/docs")
    uvicorn.run(app, host=host, port=port, reload=reload)

if __name__ == "__main__":
    main()