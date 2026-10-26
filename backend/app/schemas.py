"""Pydantic response models for the API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response of the health check endpoint."""

    status: str
