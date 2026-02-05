import logging
import sys
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.endpoints import ranking

# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Include Routers
app.include_router(ranking.router, prefix=f"{settings.API_V1_STR}", tags=["ranking"])

@app.get("/")
def health_check():
    return {"status": "ok", "message": "AI Ranking System is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
