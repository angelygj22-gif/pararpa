from playwright.async_api import Browser

from src.extractor_datos import ExtractorDatos

URL_SUNAT = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"

SELECTOR_POR_RUC = "#btnPorRuc"
SELECTOR_BUSQUEDA = "#txtRuc"
SELECTOR_BOTON = "#btnAceptar"


async def consultar_ruc(browser: Browser, ruc: str) -> dict:
    page = await browser.new_page()
    try:
        await page.goto(URL_SUNAT, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        await page.locator(SELECTOR_POR_RUC).wait_for(state="visible", timeout=10000)
        await page.locator(SELECTOR_POR_RUC).click()
        await page.wait_for_timeout(1000)

        await page.locator(SELECTOR_BUSQUEDA).clear()
        await page.locator(SELECTOR_BUSQUEDA).fill(ruc)
        await page.wait_for_timeout(1000)

        await page.locator(SELECTOR_BOTON).click()

        try:
            await page.wait_for_url("**/jcrS00Alias*", timeout=15000)
        except Exception:
            return _respuesta_error(ruc, "NO EXISTE")

        await page.wait_for_timeout(2000)

        html = await page.content()
        datos = ExtractorDatos().extraer(html)

        return _mapear_datos(datos, ruc)

    except Exception:
        return _respuesta_error(ruc, "SUNAT fuera de servicio")

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


def _respuesta_error(ruc: str, motivo: str) -> dict:
    detalle = "RUC no encontrado en el padrón de SUNAT" if motivo == "NO EXISTE" else "Error al conectar con SUNAT"

    return {
        "ruc": ruc,
        "razon_social": "",
        "tipo_contribuyente": "",
        "nombre_comercial": "",
        "fecha_inscripcion": "",
        "fecha_inicio_actividades": "",
        "estado": motivo,
        "condicion": "",
        "domicilio_fiscal": "",
        "sistema_emision": "",
        "actividad_comercio_exterior": "",
        "sistema_contabilidad": "",
        "emisor_electronico_desde": "",
        "actividades_economicas": [],
        "detalle": detalle,
        "status": "Error",
    }
