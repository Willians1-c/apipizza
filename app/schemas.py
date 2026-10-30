from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator

# Los montos viajan como número en el JSON (ej. 190.0), calculados con Decimal en el servidor.
Dinero = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]
Metodo = Literal["domicilio", "recoger"]


# ---------- Catálogo ----------
class TamanoPrecioOut(BaseModel):
    id_pizza_tamano: int
    tamano: str
    precio: Dinero
    disponible: bool


class PizzaOut(BaseModel):
    id_pizza: int
    sabor: str
    descripcion: str | None
    imagen_url: str
    etiqueta: str | None
    destacado: bool
    aplica_promo: bool
    precio_desde: Dinero | None
    tamanos: list[TamanoPrecioOut]


class MasaOut(BaseModel):
    id_masa: int
    nombre: str
    precio_extra: Dinero


# ---------- Carrito ----------
class ItemAdd(BaseModel):
    id_pizza_tamano: int
    id_masa: int
    cantidad: int = Field(default=1, ge=1, le=20)


class ItemUpdate(BaseModel):
    cantidad: int = Field(ge=1, le=20)


class ItemOut(BaseModel):
    id_carrito_pizza: int
    id_pizza_tamano: int
    sabor: str
    imagen_url: str
    tamano: str
    precio_tamano: Dinero
    masa: str
    extra_masa: Dinero
    cantidad: int
    precio_unitario: Dinero
    subtotal_linea: Dinero
    unidades_gratis: int
    descuento_linea: Dinero
    total_linea: Dinero


class ResumenOut(BaseModel):
    total_pizzas: int
    subtotal: Dinero
    costo_envio: Dinero
    descuento: Dinero
    total: Dinero
    promo_aplicada: bool
    promo_nombre: str | None


class CarritoOut(BaseModel):
    id_carrito: int
    estado: str
    expira_en: datetime | None
    metodo: Metodo
    items: list[ItemOut]
    resumen: ResumenOut


# ---------- Checkout / Ticket ----------
class CheckoutIn(BaseModel):
    nombre_cliente: str = Field(min_length=3, max_length=100)
    telefono: str = Field(min_length=7, max_length=20, pattern=r"^[0-9+\-\s()]+$")
    metodo: Metodo
    direccion: str | None = Field(default=None, max_length=255)
    indicaciones: str | None = Field(default=None, max_length=255)

    @field_validator("nombre_cliente", "telefono", "direccion", "indicaciones", mode="before")
    @classmethod
    def limpiar(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def direccion_si_domicilio(self):
        if self.metodo == "domicilio" and not self.direccion:
            raise ValueError("La dirección es obligatoria para envío a domicilio")
        return self


class ClienteOut(BaseModel):
    nombre_cliente: str
    telefono: str
    metodo: Metodo
    direccion: str | None
    indicaciones: str | None


class TicketOut(BaseModel):
    folio: str
    estado: str
    created_at: datetime
    cliente: ClienteOut
    items: list[ItemOut]
    resumen: ResumenOut


class EstadoUpdate(BaseModel):
    estado: Literal["en_preparacion", "en_camino", "listo_para_recoger", "entregado", "cancelado"]
