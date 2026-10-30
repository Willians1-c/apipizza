"""
Motor de cálculo del carrito (HU13: recalcular subtotales y total sin intervención manual).

Reglas:
- precio_unitario = precio del tamaño + extra de la masa.
- Promo "Martes de Locura 2x1": solo pedidos a DOMICILIO, pizzas MEDIANAS de sabor
  Pepperoni u Hawaiana. Las unidades elegibles se ordenan de mayor a menor precio y se
  forman parejas consecutivas; en cada pareja la de menor valor es gratis.
- Total = subtotal + envío - descuento.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..config import settings
from ..models import CarritoPizza
from ..utils import money


@dataclass
class LineaCalculada:
    item: CarritoPizza
    unidades_gratis: int
    descuento: Decimal
    subtotal: Decimal
    total: Decimal


@dataclass
class Calculo:
    lineas: list[LineaCalculada]
    total_pizzas: int
    subtotal: Decimal
    costo_envio: Decimal
    descuento: Decimal
    total: Decimal
    promo_aplicada: bool


def promo_vigente(momento: datetime, metodo: str) -> bool:
    if metodo != "domicilio":
        return False
    return settings.promo_forzada or momento.weekday() == settings.promo_dia_semana


def sabor_aplica_promo(sabor: str) -> bool:
    s = sabor.lower()
    return any(x.lower() in s for x in settings.promo_sabores)


def es_elegible(item: CarritoPizza) -> bool:
    pt = item.pizza_tamano
    return pt.tamano.nombre.lower() == settings.promo_tamano.lower() and sabor_aplica_promo(pt.pizza.sabor)


def precio_vigente(item: CarritoPizza) -> Decimal:
    return money(item.pizza_tamano.precio + item.masa.precio_extra)


def sincronizar_precios(items) -> None:
    """Actualiza el snapshot precio_unitario con el catálogo actual (solo carritos activos)."""
    for it in items:
        nuevo = precio_vigente(it)
        if it.precio_unitario != nuevo:
            it.precio_unitario = nuevo


def calcular_resumen(items, metodo: str, promo_activa: bool) -> Calculo:
    items = sorted(items, key=lambda i: i.id_carrito_pizza)
    gratis_por_item: dict[int, int] = defaultdict(int)
    promo_aplicada = False

    if promo_activa and metodo == "domicilio":
        unidades: list[tuple[Decimal, int]] = []
        for it in items:
            if es_elegible(it):
                unidades.extend([(it.precio_unitario, it.id_carrito_pizza)] * it.cantidad)
        unidades.sort(key=lambda u: u[0], reverse=True)
        for _, id_item in unidades[1::2]:  # la menor de cada pareja
            gratis_por_item[id_item] += 1
        promo_aplicada = bool(gratis_por_item)

    lineas = []
    for it in items:
        sub = money(it.precio_unitario * it.cantidad)
        gratis = gratis_por_item[it.id_carrito_pizza]
        desc = money(it.precio_unitario * gratis)
        lineas.append(LineaCalculada(it, gratis, desc, sub, sub - desc))

    subtotal = sum((l.subtotal for l in lineas), Decimal("0.00"))
    descuento = sum((l.descuento for l in lineas), Decimal("0.00"))
    envio = money(settings.costo_envio) if (metodo == "domicilio" and lineas) else Decimal("0.00")

    return Calculo(
        lineas=lineas,
        total_pizzas=sum(i.cantidad for i in items),
        subtotal=subtotal,
        costo_envio=envio,
        descuento=descuento,
        total=money(subtotal + envio - descuento),
        promo_aplicada=promo_aplicada,
    )
