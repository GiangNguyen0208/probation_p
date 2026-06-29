import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "social_api_gateway.main:app",
        host=settings.gateway.host,
        port=settings.gateway.port,
        reload=False,
    )

if __name__ == "__main__":
    main()
