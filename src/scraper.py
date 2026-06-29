import traceback

from playwright.async_api import Browser

from src.extractor_datos import ExtractorDatos
from src.schemas import respuesta_vacia

URL_SUNAT = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"

SELECTOR_POR_RUC = "#btnPorRuc"
SELECTOR_BUSQUEDA = "#txtRuc"
SELECTOR_BOTON = "#btnAceptar"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


async def consultar_ruc(browser: Browser, ruc: str) -> dict:
    page = await browser.new_page(user_agent=USER_AGENT)
    try:
        await page.goto(URL_SUNAT, timeout=60000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        await page.locator(SELECTOR_POR_RUC).wait_for(state="visible", timeout=15000)
        await page.locator(SELECTOR_POR_RUC).click()
        await page.wait_for_timeout(1500)

        await page.locator(SELECTOR_BUSQUEDA).clear()
        await page.locator(SELECTOR_BUSQUEDA).fill(ruc)
        await page.wait_for_timeout(1500)

        await page.locator(SELECTOR_BOTON).click()

        try:
            await page.wait_for_selector("#divResultado", state="visible", timeout=20000)
        except Exception:
            contenido = await page.content()
            if "No se encontraron" in contenido:
                return respuesta_vacia(ruc, "RUC no encontrado en el padrón de SUNAT")
            pagina = await page.inner_text("body")
            resultado_ok = ruc in pagina and ("ACTIVO" in pagina or "HABIDO" in pagina)
            if not resultado_ok:
                return respuesta_vacia(ruc, "RUC no encontrado en el padrón de SUNAT")

        await page.wait_for_timeout(2000)

        html = await page.content()
        datos = ExtractorDatos().extraer(html)

        return _mapear_datos(datos, ruc)

    except Exception as e:
        detalle = f"Error: {type(e).__name__}: {str(e)[:200]}"
        print(detalle)
        traceback.print_exc()
        return respuesta_vacia(ruc, detalle, estado="SUNAT fuera de servicio")

    finally:
        try:
            await page.close()
        except Exception:
            pass


def _mapear_datos(datos: dict, ruc_original: str) -> dict:
    ruc_completo = datos.get("Número de RUC", "")
    razon_social = ""
    ruc_num = ruc_original

    if " - " in ruc_completo:
        partes = ruc_completo.split(" - ", 1)
        ruc_num = partes[0].strip()
        razon_social = partes[1].strip()

    return {
        "ruc": ruc_num,
        "razon_social": razon_social,
        "tipo_contribuyente": datos.get("Tipo Contribuyente", ""),
        "nombre_comercial": datos.get("Nombre Comercial", ""),
        "fecha_inscripcion": datos.get("Fecha de Inscripción", ""),
        "fecha_inicio_actividades": datos.get("Fecha de Inicio de Actividades", ""),
        "estado": datos.get("Estado del Contribuyente", ""),
        "condicion": datos.get("Condición del Contribuyente", ""),
        "domicilio_fiscal": datos.get("Domicilio Fiscal", ""),
        "sistema_emision": datos.get("Sistema Emisión de Comprobante", ""),
        "actividad_comercio_exterior": datos.get("Actividad Comercio Exterior", ""),
        "sistema_contabilidad": datos.get("Sistema Contabilidad", ""),
        "emisor_electronico_desde": datos.get("Emisor electrónico desde", ""),
        "actividades_economicas": datos.get("Actividades Económicas", []),
        "detalle": "Consulta exitosa",
        "status": "Exitoso",
    }
