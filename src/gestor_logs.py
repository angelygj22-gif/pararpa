# =============================================================================
# Módulo: gestor_logs.py
# Propósito: Sistema de bitácora (logging) que registra cada acción del robot
#            en un archivo de texto con timestamp. Permite trazabilidad total.
# Ciclo de vida: Fase 1 - Preparación de Entornos
# =============================================================================

import os
from datetime import datetime


class GestorLogs:
    """
    Escribe mensajes formateados con timestamp en un archivo de log
    y simultáneamente los imprime en consola para monitoreo en tiempo real.
    """

    def __init__(self, ruta_log: str):
        """
        Args:
            ruta_log: Ruta completa del archivo de log (ej: C:\\RPA_RUC\\Logs\\proceso.log)
        """
        self.ruta_log = ruta_log
        self._asegurar_directorio()

    def _asegurar_directorio(self):
        """
        Crea la estructura de carpetas del archivo de log si no existe.
        Previene errores de FileNotFoundError al escribir la primera línea.
        """
        directorio = os.path.dirname(self.ruta_log)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)

    @staticmethod
    def _formatear(mensaje: str) -> str:
        """
        Formatea el mensaje con timestamp y un ancho máximo de 120 caracteres
        para mejorar la legibilidad del log.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] {mensaje}"
        return linea

    def escribir(self, mensaje: str):
        """
        Registra un mensaje con formato: [YYYY-MM-DD HH:MM:SS] mensaje
        en el archivo de log (UTF-8 puro, sin BOM) y lo imprime en consola.

        Args:
            mensaje: Texto descriptivo de la acción realizada.
        """
        linea = self._formatear(mensaje)
        with open(self.ruta_log, "a", encoding="utf-8", newline="\n") as f:
            f.write(linea + "\n")
        print(linea)

    def escribir_separador(self):
        """
        Escribe una línea divisoria de 80 guiones para mejorar la
        legibilidad del archivo de log entre ejecuciones.
        """
        self.escribir("-" * 80)
