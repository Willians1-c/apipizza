from ..config import settings
from ..models import Carrito, Ticket
from ..schemas import CarritoOut, ClienteOut, ItemOut, ResumenOut, TicketOut
from ..utils import ahora
from .pricing import Calculo, LineaCalculada, calcular_resumen, promo_vigente


def item_out(l: LineaCalculada) -> ItemOut:
    it = l.item
    pt = it.pizza_tamano
    return ItemOut(
        id_carrito_pizza=it.id_carrito_pizza,
        id_pizza_tamano=pt.id_pizza_tamano,
        sabor=pt.pizza.sabor,
        imagen_url=pt.pizza.imagen_url,
        tamano=pt.tamano.nombre,
        precio_tamano=pt.precio,
        masa=it.masa.nombre,
        extra_masa=it.masa.precio_extra,
        cantidad=it.cantidad,
        precio_unitario=it.precio_unitario,
        subtotal_linea=l.subtotal,
        unidades_gratis=l.unidades_gratis,
        descuento_linea=l.descuento,
        total_linea=l.total,
    )


def resumen_out(c: Calculo) -> ResumenOut:
    return ResumenOut(
        total_pizzas=c.total_pizzas,
        subtotal=c.subtotal,
        costo_envio=c.costo_envio,
        descuento=c.descuento,
        total=c.total,
        promo_aplicada=c.promo_aplicada,
        promo_nombre=settings.promo_nombre if c.promo_aplicada else None,
    )


def vista_carrito(carrito: Carrito, metodo: str) -> CarritoOut:
    calc = calcular_resumen(carrito.items, metodo, promo_vigente(ahora(), metodo))
    return CarritoOut(
        id_carrito=carrito.id_carrito,
        estado=carrito.estado,
        expira_en=carrito.expira_en,
        metodo=metodo,
        items=[item_out(l) for l in calc.lineas],
        resumen=resumen_out(calc),
    )


def vista_ticket(t: Ticket) -> TicketOut:
    # El ticket es histórico: los totales salen de lo guardado, no del día/hora actual.
    # Solo se reconstruye el detalle por línea (qué pizza fue la gratis).
    con_promo = t.descuento > 0
    calc = calcular_resumen(t.carrito.items, t.metodo, promo_activa=con_promo)
    resumen = ResumenOut(
        total_pizzas=calc.total_pizzas,
        subtotal=t.subtotal,
        costo_envio=t.costo_envio,
        descuento=t.descuento,
        total=t.total,
        promo_aplicada=con_promo,
        promo_nombre=settings.promo_nombre if con_promo else None,
    )
    return TicketOut(
        folio=t.folio,
        estado=t.estado,
        created_at=t.created_at,
        cliente=ClienteOut(
            nombre_cliente=t.nombre_cliente,
            telefono=t.telefono,
            metodo=t.metodo,
            direccion=t.direccion,
            indicaciones=t.indicaciones,
        ),
        items=[item_out(l) for l in calc.lineas],
        resumen=resumen,
    )
