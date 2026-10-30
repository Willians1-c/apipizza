from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Carrito
from ..utils import ahora


def renovar(carrito: Carrito) -> None:
    carrito.expira_en = ahora() + timedelta(minutes=settings.carrito_ttl_minutos)


def obtener_carrito(db: Session, id_carrito: int) -> Carrito:
    carrito = db.get(Carrito, id_carrito)
    if not carrito:
        raise HTTPException(404, "Carrito no encontrado")
    return carrito


def obtener_carrito_activo(db: Session, id_carrito: int) -> Carrito:
    carrito = obtener_carrito(db, id_carrito)
    if carrito.estado == "finalizado":
        raise HTTPException(409, "Este carrito ya fue finalizado")
    if carrito.estado == "expirado" or (carrito.expira_en and carrito.expira_en < ahora()):
        carrito.estado = "expirado"
        db.commit()
        raise HTTPException(410, "El carrito expiró, crea uno nuevo")
    return carrito
