from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import carrito, catalogo, tickets

app = FastAPI(title="API Pizzería Chevery", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogo.router, prefix="/api")
app.include_router(carrito.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}
