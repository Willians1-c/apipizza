from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://root:root@localhost:3306/pizzeria_chevery"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    zona_horaria: str = "America/Mexico_City"

    carrito_ttl_minutos: int = 120
    max_por_linea: int = 20
    costo_envio: Decimal = Decimal("0.00")  # Suchiapa = $0

    # Promo "Martes de Locura 2x1"
    promo_nombre: str = "Martes de Locura 2×1"
    promo_dia_semana: int = 1  # lunes=0 ... martes=1
    promo_forzada: bool = False
    promo_tamano: str = "mediana"
    promo_sabores: list[str] = ["pepperoni", "hawaiana"]  # coincide por texto en PIZZA.sabor

    admin_api_key: str = "cambia-esta-clave"


settings = Settings()
