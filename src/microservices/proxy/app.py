import os
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware



SERVICES = {
    "movies": os.getenv("MOVIES_SERVICE_URL", "http://movies-service:8081"),
    "monolith": os.getenv("MONOLITH_SERVICE_URL", "http://monolith:8080")
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cinema API Gateway", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


class ServiceClient:
    def __init__(self):
        self.timeout = 30.0
        self.services = SERVICES

    async def _make_request(
        self,
        service_name: str,
        method: str,
        path: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        query: Optional[dict] = None,
    ):
        base_url = self.services.get(service_name)
        if not base_url:
            raise HTTPException(status_code=500, detail=f"Service {service_name} not configured")

        url = f"{base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:

            response = await client.request(method=method, url=url, json=data, headers=headers, params=query)

            if response.status_code >= 400:
                logger.error(f"Service {service_name} error: {response.status_code} - {response.text}")

            return response.json()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/movies")
async def create_movie(request: dict):
    response = await ServiceClient()._make_request("movies", "POST", "/api/movies", request)
    return response


@app.get("/api/movies")
async def get_movies(id: str | None = None):
    response = await ServiceClient()._make_request("movies", "GET", "/api/movies", query={"id": id})
    return response


@app.get("/api/users")
async def get_users():
    response = await ServiceClient()._make_request("monolith", "GET", "/api/users")
    return response