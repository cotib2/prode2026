from fastapi import FastAPI # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from app.api.partidos import router as partidos_router

app = FastAPI(
    title="Backend Prode 2026",
    description="API para procesar resultados del Mundial y calcular puntos",
    version="1.0.0"
)


origins = [
    "https://prode2026-khaki.vercel.app",  # Tu frontend en Vercel
    "http://localhost:5173",               # Por si testeás en local con Vite
    "http://localhost:3000"
]

# 🚀 3. Le clavamos el middleware a la app antes de los routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Permite peticiones desde tus dominios
    allow_credentials=True,
    allow_methods=["*"],              # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],              # Permite todos los headers
)

# Incluimos el router de partidos en la app central
app.include_router(partidos_router)

@app.get("/")
def home():
    return {"message": "¡Backend del Prode 2026 funcionando de diez! ⚽"}