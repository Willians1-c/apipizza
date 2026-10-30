from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import uuid4

from ..config import settings
from ..database import get_db
from ..models import Carrito, CarritoPizza, Masa, PizzaTamano, Ticket
from ..schemas import CarritoOut, CheckoutIn, ItemAdd, ItemUpdate, Metodo, TicketOut
from ..services.carritos import obtener_carrito_activo, renovar
from ..services.presenters import vista_carrito, vista_ticket
from ..services.pricing import calcular_resumen, promo_vigente, sincronizar_precios, precio_vigente
from ..utils import ahora

router = APIRouter(prefix="/carritos", tags=["Carrito (HU05 / HU13)"])


def _cerrar_y_responder(db: Session, carrito: Carrito, metodo: str) -> CarritoOut:
    """Persiste, renueva expiración, re-sincroniza precios y devuelve el carrito RECALCULADO (HU13)."""
    db.flush()
    db.expire(carrito, ["items"])
    sincronizar_precios(carrito.items)
    renovar(carrito)
    db.commit()
    return vista_carrito(carrito, metodo)


def _stock_otras_lineas(carrito: Carrito, id_pizza_tamano: int, excluir: int | None = None) -> int:
    return sum(
        i.cantidad
        for i in carrito.items
        if i.id_pizza_tamano == id_pizza_tamano and i.id_carrito_pizza != excluir
    )


@router.post("", response_model=CarritoOut, status_code=201, summary="Crear carrito")
def crear_carrito(metodo: Metodo = "domicilio", db: Session = Depends(get_db)):
    carrito = Carrito(estado="activo")
    renovar(carrito)
    db.add(carrito)
    db.commit()
    return vista_carrito(carrito, metodo)


@router.get("/{id_carrito}", response_model=CarritoOut, summary="Ver carrito con totales recalculados")
def ver_carrito(id_carrito: int, metodo: Metodo = "domicilio", db: Session = Depends(get_db)):
    """Llamar con `?metodo=recoger` cuando el usuario cambie el toggle 'Recoger en Tienda'
    (la promo 2×1 solo aplica a domicilio)."""
    carrito = obtener_carrito_activo(db, id_carrito)
    sincronizar_precios(carrito.items)
    db.commit()
    return vista_carrito(carrito, metodo)


@router.post("/{id_carrito}/items", response_model=CarritoOut, summary="Agregar pizza")
def agregar_item(id_carrito: int, datos: ItemAdd, metodo: Metodo = "domicilio", db: Session = Depends(get_db)):
    carrito = obtener_carrito_activo(db, id_carrito)

    pt = db.get(PizzaTamano, datos.id_pizza_tamano)
    if not pt or not pt.pizza.activo:
        raise HTTPException(404, "Esa pizza o tamaño no está disponible")
    masa = db.get(Masa, datos.id_masa)
    if not masa or not masa.activo:
        raise HTTPException(404, "Ese tipo de masa no está disponible")

    existente = next(
        (i for i in carrito.items if i.id_pizza_tamano == pt.id_pizza_tamano and i.id_masa == masa.id_masa),
        None,
    )
    cantidad_linea = (existente.cantidad if existente else 0) + datos.cantidad
    if cantidad_linea > settings.max_por_linea:
        raise HTTPException(422, f"Máximo {settings.max_por_linea} piezas por producto")
    if _stock_otras_lineas(carrito, pt.id_pizza_tamano) + datos.cantidad > pt.stock:
        raise HTTPException(409, f"Stock insuficiente de {pt.pizza.sabor} {pt.tamano.nombre}")

    if existente:
        existente.cantidad = cantidad_linea
    else:
        db.add(
            CarritoPizza(
                id_carrito=carrito.id_carrito,
                id_pizza_tamano=pt.id_pizza_tamano,
                id_masa=masa.id_masa,
                cantidad=datos.cantidad,
                precio_unitario=pt.precio + masa.precio_extra,
            )
        )
    return _cerrar_y_responder(db, carrito, metodo)


def _buscar_item(carrito: Carrito, id_item: int) -> CarritoPizza:
    item = next((i for i in carrito.items if i.id_carrito_pizza == id_item), None)
    if not item:
        raise HTTPException(404, "Ese producto no está en el carrito")
    return item


@router.patch("/{id_carrito}/items/{id_item}", response_model=CarritoOut, summary="Cambiar cantidad (+ / -)")
def modificar_cantidad(
    id_carrito: int, id_item: int, datos: ItemUpdate, metodo: Metodo = "domicilio", db: Session = Depends(get_db)
):
    carrito = obtener_carrito_activo(db, id_carrito)
    item = _buscar_item(carrito, id_item)
    pt = item.pizza_tamano
    if _stock_otras_lineas(carrito, pt.id_pizza_tamano, excluir=item.id_carrito_pizza) + datos.cantidad > pt.stock:
        raise HTTPException(409, f"Stock insuficiente de {pt.pizza.sabor} {pt.tamano.nombre}")
    item.cantidad = datos.cantidad
    return _cerrar_y_responder(db, carrito, metodo)


@router.delete("/{id_carrito}/items/{id_item}", response_model=CarritoOut, summary="Eliminar producto")
def eliminar_item(id_carrito: int, id_item: int, metodo: Metodo = "domicilio", db: Session = Depends(get_db)):
    carrito = obtener_carrito_activo(db, id_carrito)
    db.delete(_buscar_item(carrito, id_item))
    return _cerrar_y_responder(db, carrito, metodo)


@router.post("/{id_carrito}/checkout", response_model=TicketOut, status_code=201, summary="Confirmar pedido")
def confirmar_pedido(id_carrito: int, datos: CheckoutIn, db: Session = Depends(get_db)):
    carrito = obtener_carrito_activo(db, id_carrito)
    if not carrito.items:
        raise HTTPException(422, "El carrito está vacío")
    sincronizar_precios(carrito.items)

    # Stock: bloqueo de filas para evitar sobreventa entre pedidos simultáneos
    requerido: dict[int, int] = defaultdict(int)
    for it in carrito.items:
        requerido[it.id_pizza_tamano] += it.cantidad
    filas = db.scalars(
        select(PizzaTamano).where(PizzaTamano.id_pizza_tamano.in_(list(requerido))).with_for_update()
    ).all()
    for pt in filas:
        if not pt.pizza.activo:
            raise HTTPException(409, f"{pt.pizza.sabor} ya no está disponible")
        if pt.stock < requerido[pt.id_pizza_tamano]:
            raise HTTPException(409, f"Stock insuficiente de {pt.pizza.sabor} {pt.tamano.nombre}")
    for pt in filas:
        pt.stock -= requerido[pt.id_pizza_tamano]

    momento = ahora()
    calc = calcular_resumen(carrito.items, datos.metodo, promo_vigente(momento, datos.metodo))

    ticket = Ticket(
        id_carrito=carrito.id_carrito,
        folio=f"TMP-{uuid4().hex[:12]}",  # se reemplaza con el consecutivo real
        nombre_cliente=datos.nombre_cliente,
        telefono=datos.telefono,
        metodo=datos.metodo,
        direccion=datos.direccion if datos.metodo == "domicilio" else None,
        indicaciones=datos.indicaciones,
        subtotal=calc.subtotal,
        costo_envio=calc.costo_envio,
        descuento=calc.descuento,
        total=calc.total,
        estado="recibido",
    )
    db.add(ticket)
    db.flush()
    ticket.folio = f"CHV-{momento.year}-{ticket.id_ticket:03d}"
    carrito.estado = "finalizado"
    db.commit()
    return vista_ticket(ticket)
