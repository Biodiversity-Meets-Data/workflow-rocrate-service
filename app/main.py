from fastapi import FastAPI

from app.api.workflows import router as workflows_router

app = FastAPI()

app.include_router(workflows_router)
