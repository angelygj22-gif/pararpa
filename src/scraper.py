from playwright.sync_api import Browser, Page

from src.extractor_datos import ExtractorDatos

URL_SUNAT = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"

SELECTOR_POR_RUC = "#btnPorRuc"
SELECTOR_BUSQUEDA = "#txtRuc"
SELECTOR_BOTON = "#btnAceptar"


def consultar_ruc(browser: Browser, ruc: str) -> dict:
    page = browser.new_page()
    try:
        page.goto(URL_SUNAT, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        page.locator(SELECTOR_POR_RUC).wait_for(state="visible", timeout=10000)
        page.locator(SELECTOR_POR_RUC).click()
        page.wait_for_timeout(1000)

        page.locator(SELECTOR_BUSQUEDA).clear()
        page.locator(SELECTOR_BUSQUEDA).fill(ruc)
        page.wait_for_timeout(1000)

        page.locator(SELECTOR_BOTON).click()

        try:
            page.wait_for_url("**/jcrS00Alias*", timeout=15000)
        except Exception:
            return _respuesta_error(ruc, "NO EXISTE")

        page.wait_for_timeout(2000)

        html = page.content()
        datos = ExtractorDatos().extraer(html)

        return _mapear_datos(datos, ruc)

    except Exception as e:
        return _respuesta_error(ruc, "SUNAT fuera de servicio")

    finally:
        try:
            page.close()
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
        "estado": datos.get("Estado del Contribuyente", ""),
        "condicion": datos.get("Condición del Contribuyente", ""),
        "status": "Exitoso",
    }


def _respuesta_error(ruc: str, motivo: str) -> dict:
    return {
        "ruc": ruc,
        "razon_social": "",
        "estado": motivo,
        "condicion": "",
        "status": "Error",
    }
