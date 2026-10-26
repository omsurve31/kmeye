"""FastAPI application: routes and middleware."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX, API_TITLE, CORS_ALLOWED_ORIGINS
from app.schemas import HealthResponse

app = FastAPI(title=API_TITLE)

# Read-only API: only GET is allowed cross-origin.
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOWED_ORIGINS, allow_methods=["GET"])


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    """Report that the service is running."""
    return HealthResponse(status="ok")
