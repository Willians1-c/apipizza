# API Pizzería Chevery (FastAPI + SQLAlchemy + MySQL)

## Correr
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # edita DATABASE_URL
uvicorn app.main:app --reload
```
Docs interactivas: http://localhost:8000/docs

Requiere que ya hayas corrido tu script SQL y tengas datos en PIZZA, TAMANO, PIZZA_TAMANO y MASA.

## Probar (no toca MySQL, usa SQLite temporal)
```bash
pip install -r requirements-dev.txt && pytest -q
```
