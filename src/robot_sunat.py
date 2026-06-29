# =============================================================================
# Módulo: robot_sunat.py
# Propósito: Núcleo del robot RPA. Orquesta las 5 fases del ciclo de vida:
#   F1 - Inicialización Dinámica    (Lectura config, apertura Excel y Edge)
#   F2 - Control de Entradas        (For Each + filtros de fila vacía y duplicado)
#   F3 - Resiliencia ante Caídas    (Retry 1-3 con manejo de errores)
#   F4 - Procesamiento de Archivos  (Extraer HTML, generar PDF, reportar éxito)
#   F5 - Cierre y Notificación      (Cerrar recursos, log final, enviar email)
#
# Dependencias: Playwright (sync_api), openpyxl
# =============================================================================

import os
import time
import zipfile
from datetime import datetime

from src.lector_config import LectorConfig
from src.gestor_logs import GestorLogs
from src.gestor_excel import GestorExcel
from src.navegador import Navegador
from src.conversor_pdf import ConversorPDF
from src.notificador import Notificador
from src.extractor_datos import ExtractorDatos


class RobotSunat:
    """
    Orquestador principal del robot.
    Cada fase del ciclo de vida está implementada en un método privado
    para mantener el código modular, testeable y legible.
    """

    def __init__(self, ruta_config: str = "config.json"):
        """
        Inicializa todos los componentes del robot a partir del archivo
        de configuración externo. Ninguna ruta está hardcodeada.

        Args:
            ruta_config: Ruta al archivo config.json
        """
        # Cargar configuración dinámica (Fase 1 - Lectura de Configuración)
        self.config = LectorConfig(ruta_config)

        # Inicializar gestores
        self.log = GestorLogs(self.config.ruta_logs)
        self.excel = GestorExcel(
            self.config.ruta_excel,
            self.config.hoja_excel,
            columna_ruc=self.config.columna_ruc,
            columna_estado=self.config.columna_estado,
            columna_detalle=self.config.columna_detalle,
            columna_nombre="A"  # nombre de empresa en columna A
        )

        # Obtener selectores desde el config (adaptables al portal real)
        sel = self.config.selectores_sunat
        self.selector_por_ruc = sel.get("botonPorRuc", "#btnPorRuc")
        self.selector_busqueda = sel.get("inputBusqueda", "#txtNumeroDocumento")
        self.selector_boton = sel.get("botonBuscar", "#btnAceptar")
        self.selector_resultados = sel.get("tablaResultados", "#divResultado table tbody tr")
        self.selector_sin_resultados = sel.get("mensajeSinResultados", "#divResultado:has-text('No se encontraron')")
        self.selector_frame = sel.get("framePrincipal", "")

        # Componentes de navegación, conversión y notificación
        self.navegador = Navegador(headless=False)
        self.conversor = ConversorPDF(self.config.ruta_pdf, self.config.ruta_html)
        self.notificador = Notificador(self.config.email_config)

        # Variables de control de ejecución
        self.tiempo_inicio = None
        self.tiempo_fin = None
        self.procesados = 0
        self.errores = 0

    # =========================================================================
    #  MÉTODO PRINCIPAL - PUNTO DE ENTRADA DEL ROBOT
    # =========================================================================

    def ejecutar(self):
        """
        Método público que dispara el ciclo de vida completo del robot.
        Está envuelto en try/finally para garantizar el cierre ordenado
        de recursos incluso si ocurre una excepción no controlada.
        """
        self.log.escribir_separador()
        self.log.escribir("=== INICIO DEL PROCESO ROBOT SUNAT ===")
        self.tiempo_inicio = time.time()

        try:
            # Fase 1: Abrir todos los recursos
            self._fase1_inicializacion()

            # Fase 2-4: Bucle principal de procesamiento
            self._fase2_bucle_principal()

        except Exception as e:
            # Captura errores críticos que detengan todo el proceso
            self.log.escribir(f"ERROR CRÍTICO EN EL PROCESO: {e}")
            self.errores += 1
            raise
        finally:
            # Fase 5: Siempre ejecuta el cierre, incluso si hubo error
            self._fase5_cierre()

    # =========================================================================
    #  FASE 1: INICIALIZACIÓN DINÁMICA (Desacoplamiento)
    # =========================================================================

    def _fase1_inicializacion(self):
        """
        Prepara todos los entornos necesarios para la ejecución:
          1. Registra la configuración cargada en el log.
          2. Abre el archivo Excel y carga los registros en memoria.
          3. Inicializa el indexador de celdas %FilaIndex% = 2.
          4. Abre Microsoft Edge y navega al portal de SUNAT.
        """
        self.log.escribir("--- FASE 1: Inicialización Dinámica ---")
        self.log.escribir(f"Configuración cargada desde: {self.config.ruta_config}")
        self.log.escribir(f"Ruta de logs: {self.config.ruta_logs}")
        self.log.escribir(f"Ruta de Excel: {self.config.ruta_excel}")
        self.log.escribir(f"URL SUNAT: {self.config.url_sunat}")
        self.log.escribir(f"Ruta compartida: {self.config.ruta_compartida}")
        self.log.escribir(f"Ruta PDFs: {self.config.ruta_pdf}")
        self.log.escribir(f"Ruta HTMLs: {self.config.ruta_html}")

        # --- Crear carpetas automáticamente ---
        for carpeta in [self.config.ruta_compartida, self.config.ruta_pdf,
                        self.config.ruta_html,
                        os.path.dirname(self.config.ruta_logs)]:
            if not os.path.exists(carpeta):
                os.makedirs(carpeta, exist_ok=True)
                self.log.escribir(f"Carpeta creada: {carpeta}")

        # --- Apertura del Excel ---
        self.excel.abrir()
        self.log.escribir(f"Excel abierto. Total filas a procesar: {self.excel.total_filas}")
        self.log.escribir(f"Indexador de filas inicializado en: {self.excel.fila_index}")

        # --- Apertura del navegador ---
        self.navegador.abrir()
        try:
            self.navegador.ir_a(self.config.url_sunat)
            self.log.escribir("Navegador Microsoft Edge lanzado y navegando hacia SUNAT")
        except Exception as e:
            self.log.escribir(f"Error al navegar a SUNAT: {e}. Continuando de todas formas...")

        # --- Configurar frame si el portal lo requiere ---
        if self.selector_frame:
            self.log.escribir(f"Configurando frame: {self.selector_frame}")
            self.navegador.configurar_frame(self.selector_frame)

        # Pequeña pausa post-navegación para evitar detección de robot
        self.navegador.esperar(self.config.tiempo_espera)

    # =========================================================================
    #  FASE 2: CONTROL DE ENTRADAS Y FILTROS DE OPTIMIZACIÓN (For Each)
    # =========================================================================

    def _fase2_bucle_principal(self):
        """
        Itera sobre cada fila del Excel aplicando filtros de seguridad:
          - Filtro 1: Control de Filas Vacías (Input sin Datos).
          - Filtro 2: Control de RUC Repetido (Duplicados).
          - Si pasa ambos filtros, avanza a Fase 3 (resiliencia) y Fase 4 (éxito).
        """
        self.log.escribir("--- FASE 2: Bucle de Procesamiento For Each ---")

        # Recorre mientras haya filas en el Excel
        while self.excel.fila_index <= self.excel.total_filas:
            ruc = self.excel.obtener_ruc()
            self.log.escribir(f"Procesando fila {self.excel.fila_index} | RUC: {ruc or '(vacío)'}")

            # Filtro 1: Si el RUC está vacío, salta esta fila
            if not self._filtro_fila_vacia(ruc):
                continue

            # Filtro 2: Si el RUC ya fue procesado (archivo existente), salta
            if not self._filtro_duplicado(ruc):
                continue

            # Fase 3 y 4: Consulta web y procesamiento
            nombre_empresa = self.excel.obtener_nombre_empresa()
            if self._fase3_resiliencia(ruc):
                self._fase4_exito(ruc, nombre_empresa)

    # -------------------------------------------------------------------------
    #  FILTRO 1: Control de Filas Vacías
    # -------------------------------------------------------------------------

    def _filtro_fila_vacia(self, ruc: str) -> bool:
        """
        Evalúa si el RUC actual está en blanco.

        Si está vacío:
          - Escribe Estado: "Error", Detalle: "No hay ruc en la fila"
          - Incrementa el indexador y salta al siguiente registro.

        Returns:
            bool: True si el RUC tiene datos, False si está vacío.
        """
        if not ruc:
            self.excel.escribir_estado("Error", "No hay ruc en la fila")
            self.log.escribir(
                f"FILTRO 1 - Fila vacía en fila {self.excel.fila_index}. "
                f"Saltando al siguiente registro."
            )
            self.excel.avanzar_fila()
            self.errores += 1
            return False
        return True

    # -------------------------------------------------------------------------
    #  FILTRO 2: Control de RUC Repetido (Duplicados)
    # -------------------------------------------------------------------------

    def _filtro_duplicado(self, ruc: str) -> bool:
        """
        Verifica si ya existe algún archivo (.html o .pdf) que contenga
        este RUC en el nombre, dentro de las carpetas pdf/ y html/.
        Si existe, se trata de un duplicado o ejecución previa.

        Returns:
            bool: True si es un RUC nuevo, False si ya fue procesado.
        """
        for carpeta in [self.config.ruta_pdf, self.config.ruta_html]:
            if not os.path.exists(carpeta):
                continue
            for archivo in os.listdir(carpeta):
                if ruc in archivo and (archivo.endswith(".html") or archivo.endswith(".pdf")):
                    self.excel.escribir_estado("Error", "RUC repetido o ya procesado")
                    self.log.escribir(
                        f"FILTRO 2 - RUC repetido/ya procesado: {ruc}. "
                        f"Archivo '{archivo}' existente en {carpeta}. Saltando."
                    )
                    self.excel.avanzar_fila()
                    self.errores += 1
                    return False
        return True

    # =========================================================================
    #  FASE 3: RESILIENCIA ANTE CAÍDAS Y EXTRACCIÓN DE DATOS
    # =========================================================================

    def _fase3_resiliencia(self, ruc: str) -> bool:
        """
        Bloque de reintentos (Loop Intento 1 to N) diseñado para soportar
        microcortes de internet o saturación del servidor SUNAT.

        Flujo:
          1. Inyecta el RUC en la barra de búsqueda.
          2. Hace clic en buscar.
          3. Evalúa si hay resultados (RowsCount > 0).
          4. Si la web falla, el catch absorbe el error y reintenta.

        Args:
            ruc: Número de RUC a consultar.

        Returns:
            bool: True si la consulta fue exitosa, False si falló o el RUC no existe.
        """
        self.log.escribir(f"--- FASE 3: Extracción con Resiliencia para RUC {ruc} ---")

        for intento in range(1, self.config.max_intentos + 1):
            try:
                self.log.escribir(f"Intento {intento}/{self.config.max_intentos} para RUC {ruc}")

                # Seleccionar la pestaña "Por RUC" (por si acaso no está activa)
                self.navegador.hacer_click(self.selector_por_ruc)
                self.navegador.esperar(1)

                # Inyectar el RUC en el campo de búsqueda del portal SUNAT
                self.navegador.escribir_en_input(self.selector_busqueda, ruc)
                self.navegador.esperar(1)

                # Hacer clic en el botón de búsqueda
                self.navegador.hacer_click(self.selector_boton)

                # --- Filtro de RUC Inexistente ---
                # SUNAT navega a /jcrS00Alias si el RUC existe.
                # Si no existe, se queda en la misma página.
                ruc_encontrado = self.navegador.esperar_url("**/jcrS00Alias*", timeout=10000)

                if not ruc_encontrado:
                    self.excel.escribir_estado("Error", "RUC no existe en SUNAT")
                    self.log.escribir(
                        f"FILTRO RUC INEXISTENTE - RUC {ruc} no encontrado "
                        f"en el padrón de SUNAT."
                    )
                    self._limpiar_para_siguiente()
                    self.excel.avanzar_fila()
                    self.errores += 1
                    return False

                self.log.escribir(f"RUC {ruc} encontrado en SUNAT. Extrayendo datos...")
                self.navegador.esperar(2)

                # Si llegamos aquí, la consulta fue exitosa
                return True

            except Exception as e:
                # Manejador de fallas técnicas. Absorbe el error y reintenta.
                self.log.escribir(
                    f"Fallo en intento {intento}/{self.config.max_intentos} "
                    f"para RUC {ruc}: {type(e).__name__}: {e}"
                )

                # Si quedan intentos, limpia y vuelve a intentar
                if intento < self.config.max_intentos:
                    self.log.escribir(
                        f"Reintentando automáticamente... "
                        f"({intento + 1}/{self.config.max_intentos})"
                    )
                    self._limpiar_para_siguiente()

        # Si se agotaron los intentos, reportar como error definitivo
        self.excel.escribir_estado(
            "Error",
            f"Fallo después de {self.config.max_intentos} intentos"
        )
        self.log.escribir(
            f"RUC {ruc} - Falló permanentemente después de "
            f"{self.config.max_intentos} intentos."
        )
        self.excel.avanzar_fila()
        self.errores += 1
        return False

    # =========================================================================
    #  FASE 4: PROCESAMIENTO DE ARCHIVOS Y TRAZABILIDAD DE ÉXITO
    # =========================================================================

    def _fase4_exito(self, ruc: str, nombre_empresa: str = ""):
        """
        Ejecuta el pipeline de éxito cuando SUNAT devuelve datos válidos:
          1. Extrae el HTML estructurado de la página.
          2. Guarda el archivo HTML local.
          3. Genera el PDF usando Playwright (page.pdf).
          4. Actualiza el Excel con Estado="Procesado".
          5. Limpia el navegador para la siguiente iteración.

        Args:
            ruc: Número de RUC que se procesó exitosamente.
            nombre_empresa: Nombre de la empresa desde el Excel (col A).
        """
        self.log.escribir(f"--- FASE 4: Procesamiento de Archivos para RUC {ruc} ---")

        try:
            # Extraer el código fuente HTML de la página de resultados
            html_raw = self.navegador.obtener_html()
            self.log.escribir("HTML extraído del portal SUNAT.")

            # Extraer datos estructurados y generar reporte profesional
            extractor = ExtractorDatos()
            datos = extractor.extraer(html_raw)
            reporte_html = extractor.generar_reporte_html(datos)
            self.log.escribir("Reporte limpio generado con datos del contribuyente.")

            # Generar el PDF con el reporte limpio
            nombre_base = f"{nombre_empresa}_{ruc}" if nombre_empresa else ruc
            ruta_pdf = self.conversor.convertir(
                nombre_base=nombre_base,
                reporte_html=reporte_html,
                page=self.navegador.page
            )

            # Determinar el detalle según si se generó PDF o solo HTML
            detalle = "Descargado con éxito"
            if ruta_pdf:
                self.log.escribir(f"PDF generado exitosamente: {ruta_pdf}")
            else:
                self.log.escribir("Reporte HTML guardado (PDF no generado).")

            # Actualizar el Excel de control con el resultado exitoso
            self.excel.escribir_estado("Procesado", detalle)
            self.log.escribir(f"RUC {ruc} - Registro marcado como Procesado.")
            self.procesados += 1

        except Exception as e:
            # Error durante el guardado o generación del PDF
            self.log.escribir(f"Error en Fase 4 para RUC {ruc}: {e}")
            self.excel.escribir_estado("Error", f"Error en procesamiento: {e}")
            self.errores += 1

        finally:
            # Siempre limpiar la navegación para la siguiente iteración
            self._limpiar_para_siguiente()
            self.excel.avanzar_fila()

    # -------------------------------------------------------------------------
    #  Helper: Limpieza entre iteraciones del bucle
    # -------------------------------------------------------------------------

    def _limpiar_para_siguiente(self):
        """
        Reinicia el estado del navegador para la próxima consulta:
          - Navega a about:blank para limpiar el DOM.
          - Vuelve a la URL principal de SUNAT.
          - Espera la carga completa.
        """
        self.navegador.limpiar_navegacion()
        try:
            self.navegador.ir_a(self.config.url_sunat)
        except Exception:
            pass

        # Re-configurar el frame si el portal lo requiere
        if self.selector_frame:
            self.navegador.configurar_frame(self.selector_frame)

        self.navegador.esperar(self.config.tiempo_espera)

    # -------------------------------------------------------------------------
    #  Helper: Crear ZIP con los PDFs generados
    # -------------------------------------------------------------------------

    def _crear_zip(self) -> str:
        """
        Comprime todos los archivos PDF generados en un solo ZIP.
        El ZIP se guarda en la ruta compartida con timestamp.

        Returns:
            str: Ruta del archivo ZIP creado, o None si no hay PDFs.
        """
        pdfs = [
            os.path.join(self.config.ruta_pdf, f)
            for f in os.listdir(self.config.ruta_pdf)
            if f.endswith(".pdf")
        ]
        if not pdfs:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_zip = os.path.join(self.config.ruta_compartida, f"Reporte_SUNAT_{timestamp}.zip")

        with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for pdf in pdfs:
                zf.write(pdf, os.path.basename(pdf))

        self.log.escribir(f"ZIP creado: {ruta_zip} ({len(pdfs)} archivos)")
        return ruta_zip

    # =========================================================================
    #  FASE 5: CIERRE DE PROCESO Y NOTIFICACIÓN
    # =========================================================================

    def _fase5_cierre(self):
        """
        Tareas de limpieza y reportería al finalizar el procesamiento:
           1. Cierra el navegador web Microsoft Edge.
           2. Guarda y cierra el archivo Excel.
           3. Calcula el tiempo total de ejecución (%TiempoTotal%).
           4. Crea un ZIP con los PDFs generados.
           5. Imprime el veredicto final en el log.
           6. Envía correo electrónico al administrador con el ZIP adjunto.
        """
        self.log.escribir("--- FASE 5: Cierre de Proceso ---")

        # 1. Cerrar navegador
        self.navegador.cerrar()
        self.log.escribir("Navegador Microsoft Edge cerrado correctamente.")

        # 2. Guardar y cerrar Excel
        self.excel.guardar_y_cerrar()
        self.log.escribir("Archivo Excel guardado y cerrado correctamente.")

        # 3. Crear ZIP con los PDFs generados
        ruta_zip = self._crear_zip()

        # 4. Calcular tiempo total de ejecución
        self.tiempo_fin = time.time()
        tiempo_total = self.tiempo_fin - self.tiempo_inicio
        minutos = int(tiempo_total // 60)
        segundos = int(tiempo_total % 60)

        # 4. Construir y escribir el reporte final en el log
        resumen = (
            f"=== REPORTE FINAL ===\n"
            f"Tiempo total de ejecución: {minutos}m {segundos}s\n"
            f"Registros procesados con éxito: {self.procesados}\n"
            f"Registros con error: {self.errores}\n"
            f"Total de filas procesadas: {self.excel.fila_index - 2}\n"
            f"========================"
        )
        self.log.escribir(resumen)

        # 6. Enviar correo de notificación al administrador
        asunto = (
            f"Reporte Robot SUNAT - "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        cuerpo = (
            f"Estimado administrador,\n\n"
            f"El proceso masivo de consulta RUC ha finalizado.\n\n"
            f"{resumen}\n\n"
            f"Se adjunta el ZIP con los PDFs generados y el Excel actualizado "
            f"con los resultados en las columnas C (Estado) y D (Detalle).\n\n"
            f"Los archivos generados se encuentran en:\n"
            f"{self.config.ruta_compartida}\n\n"
            f"Saludos,\nRobot SUNAT RPA"
        )
        enviado = self.notificador.enviar(asunto, cuerpo, archivo_adjunto=ruta_zip, archivos_extra=[self.config.ruta_excel])
        if enviado:
            self.log.escribir("Correo de notificación enviado correctamente al administrador.")
        else:
            self.log.escribir("Notificación por correo omitida o fallida (verificar credenciales SMTP).")

        self.log.escribir("=== FIN DEL PROCESO ROBOT SUNAT ===")
        self.log.escribir_separador()
