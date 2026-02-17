from fastapi import APIRouter

from src.microservices.proxy.api.movies import router as m_router

routers = APIRouter()
routers.include_router(m_router, tags=["Movies"])
