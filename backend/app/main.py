"""FastAPI application: routes and middleware."""

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import API_PREFIX, API_TITLE, CORS_ALLOWED_ORIGINS
from app.errors import NoDataError, SnapshotError
from app.routes import router
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)

app = FastAPI(title=API_TITLE)

# Read-only API: only GET is allowed cross-origin.
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOWED_ORIGINS, allow_methods=["GET"])
app.include_router(router)


@app.exception_handler(SnapshotError)
def handle_snapshot_error(request: Request, error: Exception) -> JSONResponse:
    """Log the real problem on the server; tell the client only that the data is unavailable."""
    logger.error("Snapshot problem: %s", error)
    return JSONResponse(status_code=503, content={"detail": "The data snapshot is unavailable."})


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, error: Exception) -> JSONResponse:
    """Give every invalid-input response the same shape: one readable string, input not echoed."""
    problems = cast(RequestValidationError, error).errors()
    message = "; ".join(
        f"{'.'.join(str(part) for part in problem['loc'][1:])}: {problem['msg']}"
        for problem in problems
    )
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(NoDataError)
def handle_no_data_error(request: Request, error: Exception) -> JSONResponse:
    """The request was valid but there is nothing to report for it."""
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    """Report that the service is running."""
    return HealthResponse(status="ok")
