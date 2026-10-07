import os
from fastapi import FastAPI

app = FastAPI(title="ReleaseGuard Demo App")

VERSION = os.getenv("APP_VERSION", "v1")


@app.get("/")
def root():
    return {
        "message": "Hello from ReleaseGuard",
        "version": VERSION
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": VERSION
    }

    
