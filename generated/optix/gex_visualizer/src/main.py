"""Main entry point for GEX Visualizer API."""
import uvicorn
from src.api.app import create_app
from config.settings import settings

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
