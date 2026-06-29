# =============================================================================
# Módulo: lector_config.py
# Propósito: Cargar y exponer la configuración desde el archivo JSON externo.
#            Ninguna ruta, URL o credencial está hardcodeada en el código.
# Ciclo de vida: Fase 1 - Inicialización Dinámica (Lectura de Configuración)
# =============================================================================

import json
import os


class LectorConfig:
    """
    Clase encargada de leer el archivo config.json y exponer
    cada propiedad mediante accessors (properties) tipados.
    """

    def __init__(self, ruta_config: str = "config.json"):
        """
        Args:
            ruta_config: Ruta al archivo JSON de configuración.
                         Por defecto busca en la raíz del proyecto.
        """
        self.ruta_config = ruta_config
        self.config = self._cargar()

    def _cargar(self) -> dict:
        """
        Valida que el archivo exista y lo carga en memoria.
        Lanza FileNotFoundError si no encuentra el config.
        """
        if not os.path.exists(self.ruta_config):
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: {self.ruta_config}"
            )
        with open(self.ruta_config, "r", encoding="utf-8") as f:
            return json.load(f)

    # -------------------------------------------------------------------------
    # Propiedades de rutas y URL
    # -------------------------------------------------------------------------

    @property
    def ruta_logs(self) -> str:
        """Ruta completa donde se escribirá el archivo de log del proceso."""
        return self.config["RutaLogs"]

    @property
    def ruta_excel(self) -> str:
        """Ruta del archivo Excel que contiene los RUC a procesar."""
        return self.config["RutaExcel"]

    @property
    def url_sunat(self) -> str:
        """URL base del portal de consulta de RUC de SUNAT."""
        return self.config["UrlSunat"]

    @property
    def ruta_compartida(self) -> str:
        """Directorio base donde se almacenará el ZIP."""
        return self.config["RutaCompartida"]

    @property
    def ruta_pdf(self) -> str:
        """Directorio donde se guardan los PDFs."""
        return self.config.get("RutaPDF", os.path.join(self.ruta_compartida, "pdf\\"))

    @property
    def ruta_html(self) -> str:
        """Directorio donde se guardan los HTMLs."""
        return self.config.get("RutaHTML", os.path.join(self.ruta_compartida, "html\\"))

    # -------------------------------------------------------------------------
    # Propiedades de configuración del Excel
    # -------------------------------------------------------------------------

    @property
    def hoja_excel(self) -> str:
        """Nombre de la hoja dentro del libro Excel."""
        return self.config.get("HojaExcel", "Sheet1")

    @property
    def columna_ruc(self) -> str:
        """Letra de la columna que contiene el RUC (por defecto A)."""
        return self.config.get("ColumnaRUC", "A")

    @property
    def columna_estado(self) -> str:
        """Letra de la columna donde se escribe el Estado (por defecto B)."""
        return self.config.get("ColumnaEstado", "B")

    @property
    def columna_detalle(self) -> str:
        """Letra de la columna donde se escribe el Detalle (por defecto C)."""
        return self.config.get("ColumnaDetalle", "C")

    # -------------------------------------------------------------------------
    # Propiedades de temporización y reintentos
    # -------------------------------------------------------------------------

    @property
    def tiempo_espera(self) -> int:
        """
        Segundos de espera entre acciones críticas (navegación, clics).
        Previene bloqueos por detección de automatización.
        """
        return self.config.get("TiempoEsperaSegundos", 5)

    @property
    def max_intentos(self) -> int:
        """
        Número máximo de reintentos ante fallos de red o servidor.
        Diseñado para soportar microcortes de internet o saturación de SUNAT.
        """
        return self.config.get("MaxIntentos", 3)

    # -------------------------------------------------------------------------
    # Propiedades de selectores del portal SUNAT
    # -------------------------------------------------------------------------

    @property
    def selectores_sunat(self) -> dict:
        """
        Diccionario con los selectores CSS/locators de Playwright
        para interactuar con el portal de SUNAT.
        """
        return self.config.get("SelectoresSunat", {})

    # -------------------------------------------------------------------------
    # Propiedades de notificación por correo
    # -------------------------------------------------------------------------

    @property
    def email_config(self) -> dict:
        """Configuración SMTP para el envío del reporte final."""
        return self.config.get("Email", {})
