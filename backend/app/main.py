import asyncio
from contextlib import asynccontextmanager # 👈 1. Nueva importación
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from app.api.partidos import router as partidos_router
from app.api.partidos import sincronizar_fixture

# 🚀 TAREA EN SEGUNDO PLANO
async def loop_sincronizacion():
    while True:
        await asyncio.sleep(900)  # 900 segundos = 15 minutos
        print("🔄 [BACKGROUND] Iniciando sincronización automática...")
        try:
            await run_in_threadpool(sincronizar_fixture)
            print("✅ [BACKGROUND] Sincronización completada con éxito.")
        except Exception as e:
            print(f"❌ [BACKGROUND] Error en sincronización: {e}")

# 🚀 NUEVO MANEJADOR DE CICLO DE VIDA (Reemplaza a on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Todo lo que pongas ANTES del yield se ejecuta al ARRANCAR (Startup)
    tarea_background = asyncio.create_task(loop_sincronizacion())
    
    yield # Acá es cuando la app está viva y recibiendo peticiones
    
    # Todo lo que pongas DESPUÉS del yield se ejecuta al APAGAR (Shutdown)
    tarea_background.cancel() # Buena práctica: matamos el bucle al apagar el server

# 🚀 Le pasamos el lifespan a la instancia de FastAPI
app = FastAPI(
    title="Backend Prode 2026",
    description="API para procesar resultados del Mundial y calcular puntos",
    version="1.0.0",
    lifespan=lifespan # 👈 2. Lo enchufamos acá
)

origins = [
    "https://prode2026-khaki.vercel.app",  # Tu frontend en Vercel
    "http://localhost:5173",               # Por si testeás en local con Vite
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluimos el router de partidos en la app central
app.include_router(partidos_router)

@app.get("/")
@app.head("/")
def home():
    return {"message": "¡Backend del Prode 2026 funcionando de diez! ⚽"}