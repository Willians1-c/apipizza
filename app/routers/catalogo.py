from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Masa, Pizza
from ..schemas import MasaOut, PizzaOut, TamanoPrecioOut
from ..services.pricing import sabor_aplica_promo

router = APIRouter(tags=["Catálogo"])


def pizza_out(p: Pizza) -> PizzaOut:
    tamanos = sorted(p.tamanos, key=lambda pt: (pt.tamano.orden, pt.id_pizza_tamano))
    return PizzaOut(
        id_pizza=p.id_pizza,
        sabor=p.sabor,
        descripcion=p.descripcion,
        imagen_url=p.imagen_url,
        etiqueta=p.etiqueta,
        destacado=p.destacado,
        aplica_promo=sabor_aplica_promo(p.sabor),
        precio_desde=min((pt.precio for pt in tamanos), default=None),
        tamanos=[
            TamanoPrecioOut(
                id_pizza_tamano=pt.id_pizza_tamano,
                tamano=pt.tamano.nombre,
                precio=pt.precio,
                disponible=pt.stock > 0,
            )
            for pt in tamanos
        ],
    )


@router.get("/pizzas", response_model=list[PizzaOut], summary="Menú / pizzas destacadas del inicio")
def listar_pizzas(
    destacado: bool | None = None,
    solo_promo: bool = False,
    db: Session = Depends(get_db),
):
    """`?destacado=true` para 'Pizzas Más Populares' (HU02). `?solo_promo=true` para la pestaña Promociones."""
    q = select(Pizza).where(Pizza.activo.is_(True)).order_by(Pizza.id_pizza)
    if destacado is not None:
        q = q.where(Pizza.destacado.is_(destacado))
    pizzas = [pizza_out(p) for p in db.scalars(q).all()]
    if solo_promo:
        pizzas = [p for p in pizzas if p.aplica_promo]
    return pizzas


@router.get("/pizzas/{id_pizza}", response_model=PizzaOut)
def obtener_pizza(id_pizza: int, db: Session = Depends(get_db)):
    p = db.get(Pizza, id_pizza)
    if not p or not p.activo:
        raise HTTPException(404, "Pizza no encontrada")
    return pizza_out(p)


@router.get("/masas", response_model=list[MasaOut], summary="Tipos de masa (personalización)")
def listar_masas(db: Session = Depends(get_db)):
    q = select(Masa).where(Masa.activo.is_(True)).order_by(Masa.precio_extra, Masa.id_masa)
    return db.scalars(q).all()
