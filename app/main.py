from fastapi import FastAPI

from app.api import auth, servers, sensor_data
from app.database import engine
from app.models.models import Base

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="IoT Backend API", version="0.0.1")

# Include routers
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(sensor_data.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
