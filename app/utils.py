from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from .config import settings

CENT = Decimal("0.01")


def money(valor) -> Decimal:
    """Redondea a 2 decimales (half-up). Todo el dinero se maneja con Decimal."""
    return Decimal(str(valor)).quantize(CENT, rounding=ROUND_HALF_UP)


def ahora() -> datetime:
    """Hora local del negocio, sin tzinfo (para comparar con columnas DATETIME)."""
    return datetime.now(ZoneInfo(settings.zona_horaria)).replace(tzinfo=None)
