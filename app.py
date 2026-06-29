from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright

from src.scraper import consultar_ruc
from src.schemas import respuesta_vacia

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


@app.on_event("startup")
async def startup():
    global playwright_instance, browser
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(headless=True)


@app.on_event("shutdown")
async def shutdown():
    global playwright_instance, browser
    try:
        if browser:
            await browser.close()
    except Exception:
        pass
    try:
        if playwright_instance:
            await playwright_instance.stop()
    except Exception:
        pass


@app.post("/consultar")
async def consultar(data: ConsultaRequest):
    ruc = data.ruc.strip() if data.ruc else ""

    if not ruc:
        return respuesta_vacia(detalle="RUC vacío en la solicitud")

    resultado = await consultar_ruc(browser, ruc)

    if resultado.get("estado") == "SUNAT fuera de servicio":
        raise HTTPException(status_code=500, detail="SUNAT fuera de servicio")

    return resultado
