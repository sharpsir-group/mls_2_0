"""
RESO Web API - FastAPI Application

A RESO Data Dictionary 2.0 compliant OData API backed by Databricks.

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    GET /                           - API info
    GET /health                     - Health check
    GET /odata                      - Service document
    GET /odata/$metadata            - Metadata document
    GET /odata/Property             - List properties
    GET /odata/Property('{key}')    - Get property by key
    GET /odata/Member               - List members
    GET /odata/Office               - List offices
    GET /odata/Media                - List media
    GET /odata/Contacts             - List contacts
    GET /odata/ShowingAppointment   - List showings
"""
import sys
from pathlib import Path

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import get_settings

# Import routers
from routers import property, member, office, media, contacts, showing, metadata


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(metadata.router)
    app.include_router(property.router)
    app.include_router(member.router)
    app.include_router(office.router)
    app.include_router(media.router)
    app.include_router(contacts.router)
    app.include_router(showing.router)
    
    return app


app = create_app()


@app.get("/", tags=["Info"])
async def root():
    """API information and available endpoints."""
    settings = get_settings()
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "specification": "RESO Data Dictionary 2.0",
        "odata_version": "4.0",
        "endpoints": {
            "service_document": "/odata",
            "metadata": "/odata/$metadata",
            "resources": {
                "Property": "/odata/Property",
                "Member": "/odata/Member",
                "Office": "/odata/Office",
                "Media": "/odata/Media",
                "Contacts": "/odata/Contacts",
                "ShowingAppointment": "/odata/ShowingAppointment"
            }
        },
        "documentation": "/docs"
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """Health check endpoint."""
    from services.databricks import get_databricks_connector
    
    settings = get_settings()
    
    try:
        connector = get_databricks_connector()
        result = await connector.execute_query("SELECT 1")
        databricks_status = "connected"
    except Exception as e:
        databricks_status = f"error: {str(e)[:100]}"
    
    return {
        "status": "healthy" if databricks_status == "connected" else "degraded",
        "databricks": databricks_status,
        "catalog": settings.databricks_catalog,
        "schema": settings.databricks_schema
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for OData-formatted errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "InternalServerError",
                "message": str(exc)
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

