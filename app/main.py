from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health", response_class=JSONResponse)
async def health_check():
    return {"status": "healthy"}