from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.utils.logging import get_logger
from app.routers import movies


app = FastAPI()

logger = get_logger()

app.include_router(movies.router)

@app.get("/health", response_class=JSONResponse)
async def health_check():
    return {"status": "healthy"}