#!/usr/bin/env python3
"""
Production server configuration for WhatsApp Email Assistant
"""

import os
import uvicorn
from dotenv import load_dotenv

def main():
    """Run the production server"""
    # Load environment variables
    load_dotenv()
    
    # Production configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Run with production settings
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        workers=1,     # Single worker for simplicity
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()


