from fastapi import FastAPI

from .routes import analyze, feedback, health

app = FastAPI(title="Sourcery", version="0.1.0")

app.include_router(analyze.router)
app.include_router(feedback.router)
app.include_router(health.router)