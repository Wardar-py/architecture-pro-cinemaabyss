from fastapi import APIRouter, Depends

from src.microservices.proxy.depends.dependencies import get_service_client
from src.microservices.proxy.services.client import ServiceClient

router = APIRouter(prefix="/api/movies")


@router.post("")
async def create_movie(request: dict, client: ServiceClient = Depends(get_service_client)):
    response = await client._make_request("movies", "POST", "/api/movies", request)
    return response


@router.get("")
async def get_movies(id: str | None = None, client: ServiceClient = Depends(get_service_client)):
    response = await client._make_request("movies", "GET", "/api/movies", query={"id": id})
    return response


