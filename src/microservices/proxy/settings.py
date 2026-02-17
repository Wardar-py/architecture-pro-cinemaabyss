import os

SERVICES = {
    "movies": os.getenv("MOVIES_SERVICE_URL", "http://movies-service:8081"),
}
