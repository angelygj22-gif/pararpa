# =============================================================================
# Módulo: conversor_pdf.py
# Propósito: Recibe el HTML del reporte limpio (generado por ExtractorDatos),
#            lo escribe a disco y lo convierte a PDF usando el motor nativo
#            de Playwright (Chromium), generando un documento profesional.
# Ciclo de vida: Fase 4 - Extracción y Guardado
# =============================================================================

import os
import re


class ConversorPDF:
    """
    Guarda el reporte HTML limpio y lo convierte a PDF en formato A4
    con el motor de renderizado de Chromium (Playwright page.pdf).
    """

    def __init__(self, ruta_pdf: str, ruta_html: str):
        """
        Args:
            ruta_pdf: Directorio donde se guardan los PDFs.
            ruta_html: Directorio donde se guardan los HTMLs.
        """
        self.ruta_pdf = ruta_pdf
        self.ruta_html = ruta_html
        self._asegurar_directorios()

    def _asegurar_directorios(self):
        """Crea los directorios de salida si no existen."""
        for d in [self.ruta_pdf, self.ruta_html]:
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)

    @staticmethod
    def _sanear_nombre(nombre: str) -> str:
        """
        Limpia el nombre de archivo eliminando caracteres inválidos
        para Windows y espacios redundantes.
        """
        nombre = re.sub(r'[\\/*?:"<>|]', "", nombre)
        nombre = nombre.replace("\n", " ").replace("\r", " ")
        nombre = re.sub(r'\s+', " ", nombre).strip()
        return nombre[:200]

    def convertir(self, nombre_base: str, reporte_html: str, page=None) -> str:
        """
        Guarda el reporte HTML limpio en disco y genera el PDF.

        Args:
            nombre_base: Nombre base del archivo (ej: "Interbank_20100053455").
            reporte_html: HTML del reporte limpio y profesional.
            page: Instancia de Page de Playwright para generar el PDF.

        Returns:
            str: Ruta del PDF generado, o None si falló.
        """
        nombre_base = self._sanear_nombre(nombre_base)
        ruta_html_file = os.path.join(self.ruta_html, f"{nombre_base}.html")
        ruta_pdf_file = os.path.join(self.ruta_pdf, f"{nombre_base}.pdf")

        # Guardar el HTML del reporte limpio en carpeta html/
        with open(ruta_html_file, "w", encoding="utf-8") as f:
            f.write(reporte_html)

        # Generar PDF renderizando el HTML local con Playwright
        if page:
            try:
                page.goto(f"file://{ruta_html_file}", wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(500)
                page.pdf(path=ruta_pdf_file, format="A4", print_background=True)
                return ruta_pdf_file
            except Exception as e:
                print(f"Error generando PDF: {e}")

        return None
