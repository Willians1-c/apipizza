"""Mapeo ORM de las tablas ya existentes (creadas con tu script SQL)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Pizza(Base):
    __tablename__ = "PIZZA"
    id_pizza: Mapped[int] = mapped_column(primary_key=True)
    sabor: Mapped[str] = mapped_column(String(60))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    imagen_url: Mapped[str] = mapped_column(String(255))
    etiqueta: Mapped[str | None] = mapped_column(String(30))
    destacado: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    tamanos: Mapped[list["PizzaTamano"]] = relationship(back_populates="pizza", lazy="selectin")


class Tamano(Base):
    __tablename__ = "TAMANO"
    id_tamano: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20))
    orden: Mapped[int] = mapped_column(default=0)


class PizzaTamano(Base):
    __tablename__ = "PIZZA_TAMANO"
    id_pizza_tamano: Mapped[int] = mapped_column(primary_key=True)
    id_pizza: Mapped[int] = mapped_column(ForeignKey("PIZZA.id_pizza"))
    id_tamano: Mapped[int] = mapped_column(ForeignKey("TAMANO.id_tamano"))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(default=0)

    pizza: Mapped[Pizza] = relationship(back_populates="tamanos", lazy="joined")
    tamano: Mapped[Tamano] = relationship(lazy="joined")


class Masa(Base):
    __tablename__ = "MASA"
    id_masa: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    precio_extra: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Carrito(Base):
    __tablename__ = "CARRITO"
    id_carrito: Mapped[int] = mapped_column(primary_key=True)
    estado: Mapped[str] = mapped_column(
        Enum("activo", "finalizado", "expirado", name="estado_carrito"), default="activo"
    )
    expira_en: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    items: Mapped[list["CarritoPizza"]] = relationship(
        back_populates="carrito",
        lazy="selectin",
        order_by="CarritoPizza.id_carrito_pizza",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CarritoPizza(Base):
    __tablename__ = "CARRITO_PIZZA"
    id_carrito_pizza: Mapped[int] = mapped_column(primary_key=True)
    id_carrito: Mapped[int] = mapped_column(ForeignKey("CARRITO.id_carrito", ondelete="CASCADE"))
    id_pizza_tamano: Mapped[int] = mapped_column(ForeignKey("PIZZA_TAMANO.id_pizza_tamano"))
    id_masa: Mapped[int] = mapped_column(ForeignKey("MASA.id_masa"))
    cantidad: Mapped[int] = mapped_column(default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    carrito: Mapped[Carrito] = relationship(back_populates="items")
    pizza_tamano: Mapped[PizzaTamano] = relationship(lazy="joined")
    masa: Mapped[Masa] = relationship(lazy="joined")


class Ticket(Base):
    __tablename__ = "TICKET"
    id_ticket: Mapped[int] = mapped_column(primary_key=True)
    id_carrito: Mapped[int] = mapped_column(ForeignKey("CARRITO.id_carrito"), unique=True)
    folio: Mapped[str] = mapped_column(String(20), unique=True)
    nombre_cliente: Mapped[str] = mapped_column(String(100))
    telefono: Mapped[str] = mapped_column(String(20))
    metodo: Mapped[str] = mapped_column(Enum("domicilio", "recoger", name="metodo_entrega"))
    direccion: Mapped[str | None] = mapped_column(String(255))
    indicaciones: Mapped[str | None] = mapped_column(String(255))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    costo_envio: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    estado: Mapped[str] = mapped_column(
        Enum(
            "recibido", "en_preparacion", "en_camino", "listo_para_recoger", "entregado", "cancelado",
            name="estado_ticket",
        ),
        default="recibido",
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    carrito: Mapped[Carrito] = relationship(lazy="joined")
