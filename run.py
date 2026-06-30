# run.py
#
# Application entry point.
# Run this file to start the FastAPI server.
#
# Usage:
#   python run.py
#
# The server starts at: http://localhost:8000
# API docs available at: http://localhost:8000/docs

import uvicorn
# uvicorn is an ASGI server that runs FastAPI apps.
# ASGI (Asynchronous Server Gateway Interface) is the standard for async Python web apps.

if __name__ == "__main__":
    # __name__ == "__main__" means this block only runs when you execute
    # this file directly (python run.py), not when it's imported as a module.

    uvicorn.run(
        "app.main:app",   # The FastAPI app object — "module_path:variable_name"
        host="0.0.0.0",   # Listen on all network interfaces (not just localhost)
                           # 0.0.0.0 means anyone on the local network can access it
        port=8000,         # Port number
        reload=True,       # Auto-restart when code changes (development mode)
                           # Set reload=False in production
        log_level="info",  # Uvicorn's own log level
    )
