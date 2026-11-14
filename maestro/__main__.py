"""Entrypoint: `maestro` starts the server."""

import uvicorn

from .config import settings
from .server import app


def main() -> None:
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
