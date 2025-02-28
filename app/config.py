import os

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://clau:c123456@localhost:5432/dtlabs?sslmode=disable")
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
