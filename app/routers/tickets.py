import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import PizzaTamano, Ticket
from ..schemas import EstadoUpdate, TicketOut
from ..services.presenters import vista_ticket

router = APIRouter(prefix="/tickets", tags=["Tickets"])

TRANSICIONES = {
    "recibido": {"en_preparacion", "cancelado"},
    "en_preparacion": {"en_camino", "listo_para_recoger", "cancelado"},
    "en_camino": {"entregado"},
    "listo_para_recoger": {"entregado"},
}


def requiere_admin(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key.encode(), settings.admin_api_key.encode()):
        raise HTTPException(401, "API key inválida")


def _ticket_por_folio(db: Session, folio: str) -> Ticket:
    t = db.scalar(select(Ticket).where(Ticket.folio == folio))
    if not t:
        raise HTTPException(404, "Ticket no encontrado")
    return t


@router.get("/{folio}", response_model=TicketOut, summary="Pantalla 'Pedido Confirmado'")
def ver_ticket(folio: str, db: Session = Depends(get_db)):
    return vista_ticket(_ticket_por_folio(db, folio))


@router.patch("/{folio}/estado", response_model=TicketOut, dependencies=[Depends(requiere_admin)],
              summary="Cambiar estado (cocina / reparto)")
def cambiar_estado(folio: str, datos: EstadoUpdate, db: Session = Depends(get_db)):
    t = _ticket_por_folio(db, folio)
    nuevo = datos.estado
    if nuevo not in TRANSICIONES.get(t.estado, set()):
        raise HTTPException(409, f"No se puede pasar de '{t.estado}' a '{nuevo}'")
    if nuevo == "en_camino" and t.metodo != "domicilio":
        raise HTTPException(409, "'en_camino' solo aplica a pedidos a domicilio")
    if nuevo == "listo_para_recoger" and t.metodo != "recoger":
        raise HTTPException(409, "'listo_para_recoger' solo aplica a pedidos para recoger")

    if nuevo == "cancelado":  # devolver stock
        for it in t.carrito.items:
            pt = db.scalar(select(PizzaTamano).where(PizzaTamano.id_pizza_tamano == it.id_pizza_tamano).with_for_update())
            pt.stock += it.cantidad
    t.estado = nuevo
    db.commit()
    return vista_ticket(t)
