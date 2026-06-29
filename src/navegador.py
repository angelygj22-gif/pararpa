# =============================================================================
# Módulo: navegador.py
# Propósito: Abstracción sobre Playwright para manejar Microsoft Edge.
#            Expone métodos específicos para la interacción con el portal
#            de SUNAT usando los patrones recomendados por Playwright.
# Ciclo de vida: Fase 1 (Apertura), Fase 3 (Interacción), Fase 5 (Cierre)
# =============================================================================

from playwright.sync_api import sync_playwright, Page, Browser


class Navegador:
    """
    Wrapper profesional sobre Playwright sync API.
    Oculta la complejidad de lanzar el navegador, manejar contextos
    y páginas, y proporciona métodos semánticos para el robot.

    Soporta iframes de forma transparente: si se configura un frame,
    todas las interacciones se enrutan automáticamente a través de él
    sin reemplazar la referencia a la página principal.
    """

    def __init__(self, headless: bool = False):
        """
        Args:
            headless: Modo sin interfaz gráfica (True = invisible).
                      Por defecto False para depuración visual.
        """
        self.headless = headless
        self._playwright = None
        self.browser: Browser = None
        self.page: Page = None
        # Almacena el selector del frame (ej: "iframe#iframePrincipal").
        # Cuando está configurado, todas las interacciones se hacen dentro del frame.
        self._selector_frame: str = ""

    # -------------------------------------------------------------------------
    # Helper interno: retorna el contexto correcto (Page o FrameLocator)
    # -------------------------------------------------------------------------

    def _ctx(self):
        """
        Retorna el contexto de interacción:
          - Si hay frame configurado y no está vacío: page.frame_locator(selector)
          - Si no: la page directamente
        """
        if self._selector_frame and self._selector_frame.strip():
            return self.page.frame_locator(self._selector_frame.strip())
        return self.page

    # -------------------------------------------------------------------------
    # Gestión del ciclo de vida del navegador
    # -------------------------------------------------------------------------

    def abrir(self) -> "Navegador":
        """
        Inicializa Playwright, lanza Microsoft Edge (Chromium)
        y crea una nueva página (pestaña) lista para navegar.
        """
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            headless=self.headless,
            channel="msedge"  # Usa Microsoft Edge instalado en el sistema
        )
        self.page = self.browser.new_page()
        return self

    def cerrar(self):
        """
        Cierra la página, el navegador y detiene Playwright.
        Libera todos los recursos del sistema.
        """
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Navegación
    # -------------------------------------------------------------------------

    def ir_a(self, url: str):
        """
        Navega a una URL y espera hasta que la página cargue completamente.

        Args:
            url: Dirección web completa (incluye http/https).
        """
        try:
            self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except Exception:
            self.page.goto(url, timeout=30000, wait_until="load")

    def esperar_url(self, patron: str, timeout: int = 15000) -> bool:
        """
        Espera hasta que la URL actual coincida con el patrón.
        Útil para detectar navegación a páginas de resultados.

        Args:
            patron: Patrón de URL (ej: "**/jcrS00Alias*")
            timeout: Tiempo máximo de espera en milisegundos.

        Returns:
            bool: True si la URL cambió al patrón, False si expiró el tiempo.
        """
        try:
            self.page.wait_for_url(patron, timeout=timeout)
            return True
        except Exception:
            return False

    def limpiar_navegacion(self):
        """
        Limpia la página actual navegando a about:blank.
        Previene acumulación de estado entre consultas.
        """
        self.page.goto("about:blank", wait_until="domcontentloaded")

    # -------------------------------------------------------------------------
    # Configuración de iframe
    # -------------------------------------------------------------------------

    def configurar_frame(self, selector_frame: str):
        """
        Configura un iframe para que todas las interacciones posteriores
        se ejecuten dentro de él. No reemplaza self.page, sino que
        enruta los locators a través del frame.

        Args:
            selector_frame: Selector CSS del iframe (ej: "iframe#iframePrincipal")
        """
        self._selector_frame = selector_frame

    def limpiar_frame(self):
        """
        Vuelve al contexto de la página principal (desactiva el frame).
        """
        self._selector_frame = ""

    # -------------------------------------------------------------------------
    # Interacciones con la página/frame
    # -------------------------------------------------------------------------

    def esperar(self, segundos: int):
        """
        Pausa la ejecución por una cantidad determinada de segundos.
        Usado para dar tiempo a que el servidor responda o la página renderice.

        Args:
            segundos: Tiempo de espera en segundos.
        """
        self.page.wait_for_timeout(segundos * 1000)

    def esperar_selector(self, selector: str, timeout: int = 10000):
        """
        Espera bloqueante hasta que un selector aparezca en el DOM.

        Args:
            selector: CSS selector o locator.
            timeout: Tiempo máximo de espera en milisegundos.
        """
        self._ctx().locator(selector).wait_for(state="visible", timeout=timeout)

    def escribir_en_input(self, selector: str, texto: str):
        """
        Limpia un campo de texto y escribe el valor indicado.
        Usa fill() de Playwright que es más confiable que type().

        Args:
            selector: CSS selector o locator de Playwright.
            texto: Valor a escribir en el campo.
        """
        ctx = self._ctx()
        ctx.locator(selector).clear()
        ctx.locator(selector).fill(texto)

    def hacer_click(self, selector: str):
        """
        Hace clic en un elemento de la página esperando a que sea
        visible y esté habilitado antes de interactuar.

        Args:
            selector: CSS selector o locator de Playwright.
        """
        ctx = self._ctx()
        ctx.locator(selector).wait_for(state="visible", timeout=10000)
        ctx.locator(selector).click()

    def contar_resultados(self, selector: str) -> int:
        """
        Cuenta cuántos elementos coinciden con el selector dado.
        Se usa para determinar si la SUNAT devolvió registros o no.

        Args:
            selector: CSS selector o locator.

        Returns:
            int: Cantidad de elementos encontrados.
        """
        return self._ctx().locator(selector).count()

    def obtener_html(self) -> str:
        """
        Obtiene el HTML completo de la página o frame actual.
        Útil para extraer datos estructurados o guardar el source.

        Returns:
            str: Código fuente HTML de la página/frame.
        """
        return self.page.content()

    def generar_pdf(self, ruta_salida: str):
        """
        Genera un PDF de la página actual usando el motor nativo
        de Playwright (Chromium PDF). Mucho más limpio que usar
        PowerShell con Internet Explorer.

        Args:
            ruta_salida: Ruta completa donde guardar el archivo PDF.
        """
        self.page.pdf(path=ruta_salida, format="A4", print_background=True)
