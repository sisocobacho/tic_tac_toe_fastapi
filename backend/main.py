import time
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import lifespan_setup
from backend.app.api.v1 import users, games

app = FastAPI(
    title="Tic Tac Toe API",
    lifespan=lifespan_setup,
)

# routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

app.include_router(games.router, prefix="/api/v1/games", tags=["games"])


@app.get("/")
def read_root():
    index_path = os.path.join(settings.FRONTEND_DIR, "index.html")
    return FileResponse(index_path)


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
