"""Prueba de humo del flujo completo del mockup (usa SQLite en memoria, no toca tu MySQL)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_chevery.db"
os.environ["PROMO_FORZADA"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Masa, Pizza, PizzaTamano, Tamano


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        chica, med, fam = Tamano(nombre="Chica", orden=1), Tamano(nombre="Mediana", orden=2), Tamano(nombre="Familiar", orden=3)
        pep = Pizza(sabor="La Clásica (Pepperoni)", imagen_url="p.jpg", destacado=True)
        haw = Pizza(sabor="Hawaiana", imagen_url="h.jpg", destacado=True)
        car = Pizza(sabor="Carnes Frías", imagen_url="c.jpg")
        db.add_all([chica, med, fam, pep, haw, car])
        db.flush()
        db.add_all([
            PizzaTamano(id_pizza=pep.id_pizza, id_tamano=chica.id_tamano, precio=110, stock=10),
            PizzaTamano(id_pizza=pep.id_pizza, id_tamano=med.id_tamano, precio=160, stock=10),
            PizzaTamano(id_pizza=haw.id_pizza, id_tamano=med.id_tamano, precio=170, stock=10),
            PizzaTamano(id_pizza=car.id_pizza, id_tamano=med.id_tamano, precio=195, stock=2),
        ])
        db.add_all([Masa(nombre="Tradicional", precio_extra=0), Masa(nombre="Orilla Rellena de Queso", precio_extra=30)])
        db.commit()
    return TestClient(app)


def ids(client):
    pizzas = {p["sabor"]: p for p in client.get("/api/pizzas").json()}
    masas = {m["nombre"]: m["id_masa"] for m in client.get("/api/masas").json()}
    med = lambda sabor: next(t["id_pizza_tamano"] for t in pizzas[sabor]["tamanos"] if t["tamano"] == "Mediana")
    return pizzas, masas, med


def test_catalogo(client):
    assert len(client.get("/api/pizzas?destacado=true").json()) == 2
    promo = client.get("/api/pizzas?solo_promo=true").json()
    assert {p["sabor"] for p in promo} == {"La Clásica (Pepperoni)", "Hawaiana"}


def test_flujo_mockup_2x1(client):
    _, masas, med = ids(client)
    c = client.post("/api/carritos").json()["id_carrito"]
    client.post(f"/api/carritos/{c}/items", json={"id_pizza_tamano": med("La Clásica (Pepperoni)"), "id_masa": masas["Orilla Rellena de Queso"]})
    r = client.post(f"/api/carritos/{c}/items", json={"id_pizza_tamano": med("Hawaiana"), "id_masa": masas["Tradicional"]}).json()
    assert r["resumen"] == {"total_pizzas": 2, "subtotal": 360.0, "costo_envio": 0.0, "descuento": 170.0,
                            "total": 190.0, "promo_aplicada": True, "promo_nombre": "Martes de Locura 2×1"}
    # Recoger en tienda: sin promo
    r = client.get(f"/api/carritos/{c}?metodo=recoger").json()
    assert r["resumen"]["total"] == 360.0 and not r["resumen"]["promo_aplicada"]
    # Cambiar cantidad recalcula
    item = r["items"][1]["id_carrito_pizza"]
    r = client.patch(f"/api/carritos/{c}/items/{item}", json={"cantidad": 2}).json()
    assert r["resumen"]["subtotal"] == 530.0 and r["resumen"]["descuento"] == 170.0 + 0  # 3 elegibles -> 1 gratis
    # Checkout
    body = {"nombre_cliente": "Jonathan Rodríguez", "telefono": "+52 961 123 4567", "metodo": "domicilio",
            "direccion": "Av. Central Norte #123, Suchiapa"}
    t = client.post(f"/api/carritos/{c}/checkout", json=body)
    assert t.status_code == 201, t.text
    folio = t.json()["folio"]
    assert folio.startswith("CHV-")
    got = client.get(f"/api/tickets/{folio}").json()
    assert got["resumen"]["total"] == t.json()["resumen"]["total"]
    assert client.post(f"/api/carritos/{c}/items", json={"id_pizza_tamano": med("Hawaiana"), "id_masa": masas["Tradicional"]}).status_code == 409
    # Estados
    h = {"X-API-Key": "cambia-esta-clave"}
    assert client.patch(f"/api/tickets/{folio}/estado", json={"estado": "en_preparacion"}).status_code == 422
    assert client.patch(f"/api/tickets/{folio}/estado", json={"estado": "en_preparacion"}, headers=h).json()["estado"] == "en_preparacion"
    assert client.patch(f"/api/tickets/{folio}/estado", json={"estado": "listo_para_recoger"}, headers=h).status_code == 409


def test_validaciones(client):
    _, masas, med = ids(client)
    c = client.post("/api/carritos").json()["id_carrito"]
    assert client.post(f"/api/carritos/{c}/checkout", json={"nombre_cliente": "Ana Pérez", "telefono": "9611234567", "metodo": "recoger"}).status_code == 422  # vacío
    client.post(f"/api/carritos/{c}/items", json={"id_pizza_tamano": med("Carnes Frías"), "id_masa": masas["Tradicional"], "cantidad": 2})
    r = client.post(f"/api/carritos/{c}/items", json={"id_pizza_tamano": med("Carnes Frías"), "id_masa": masas["Tradicional"]})
    assert r.status_code == 409  # stock 2
    r = client.post(f"/api/carritos/{c}/checkout", json={"nombre_cliente": "Ana Pérez", "telefono": "9611234567", "metodo": "domicilio"})
    assert r.status_code == 422  # falta dirección
