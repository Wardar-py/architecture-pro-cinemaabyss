from fastapi import Depends, HTTPException, Request

from src.microservices.proxy.services.client import ServiceClient


async def get_service_client():
    return ServiceClient()


async def validate_token(request: Request, client: ServiceClient = Depends(get_service_client)):
    """Middleware для проверки токена"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = auth_header.split(" ")[1]
    try:
        response = await client._make_request("auth", "POST", "/internal/validate", {"token": token})
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")

        return response.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
