from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine
from app.queue.client import redis_client
from app.routers import health, reels, resources, creators, logs, search, analytics
import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO if settings.APP_ENV == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("reelise_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing Reelise FastAPI backend...")
    
    # 1. Ping DB connection
    try:
        async with engine.connect() as conn:
            logger.info("Database connection validated successfully.")
    except Exception as e:
        logger.critical(f"Database connection validation failed: {str(e)}")
        
    # 2. Validate Redis
    try:
        ping_res = await redis_client.ping()
        if ping_res:
            logger.info("Redis connection validated successfully.")
    except Exception as e:
        logger.critical(f"Redis connection validation failed: {str(e)}")
        
    yield
    
    # Shutdown actions
    logger.info("Cleaning up backend client sessions...")
    await redis_client.close()
    logger.info("Reelise backend shutdown complete.")

app = FastAPI(
    title="Reelise API",
    description="Production-grade core MVP API driving the Reelise Instagram-to-Notion pipeline.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health.router)
app.include_router(reels.router)
app.include_router(resources.router)
app.include_router(creators.router)
app.include_router(logs.router)
app.include_router(search.router)
app.include_router(analytics.router)

@app.get("/")
async def root():
    return {
        "app": "Reelise API Gateway",
        "version": "1.0.0",
        "docs_url": "/docs",
        "status": "online"
    }
