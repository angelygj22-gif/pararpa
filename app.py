from concurrent.futures import ThreadPoolExecutor
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

from src.scraper import consultar_ruc

app = FastAPI(title="Consulta RUC SUNAT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsultaRequest(BaseModel):
    ruc: str


playwright_instance = None
browser = None
executor = ThreadPoolExecutor(max_workers=1)


@app.on_event("startup")
def startup():
    global playwright_instance, browser
    playwright_instance = sync_playwright().start()
    browser = playwright_instance.chromium.launch(headless=True)


@app.on_event("shutdown")
def shutdown():
    global playwright_instance, browser
    try:
        if browser:
            browser.close()
    except Exception:
        pass
    try:
        if playwright_instance:
            playwright_instance.stop()
    except Exception:
        pass
    executor.shutdown(wait=False)


@app.post("/consultar")
async def consultar(data: ConsultaRequest):
    ruc = data.ruc.strip()

    if not ruc:
        return {
            "ruc": "",
            "razon_social": "",
            "estado": "NO EXISTE",
            "condicion": "",
            "status": "Error",
        }

    loop = asyncio.get_event_loop()
    resultado = await loop.run_in_executor(executor, consultar_ruc, browser, ruc)

    if resultado.get("estado") == "SUNAT fuera de servicio":
        raise HTTPException(status_code=500, detail="SUNAT fuera de servicio")

    return resultado
