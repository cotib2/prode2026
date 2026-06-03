from fastapi import FastAPI # type: ignore
from app.api.partidos import router as partidos_router

app = FastAPI(
    title="Backend Prode 2026",
    description="API para procesar resultados del Mundial y calcular puntos",
    version="1.0.0"
)

# Incluimos el router de partidos en la app central
app.include_router(partidos_router)

@app.get("/")
def home():
    return {"message": "¡Backend del Prode 2026 funcionando de diez! ⚽"}