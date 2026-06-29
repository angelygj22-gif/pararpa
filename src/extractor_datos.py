# =============================================================================
# Módulo: extractor_datos.py
# Propósito: Extraer los datos estructurados del contribuyente desde el HTML
#            de resultados de SUNAT y generar un reporte HTML limpio y
#            profesional listo para convertir a PDF.
# =============================================================================

import re
from datetime import datetime


class ExtractorDatos:
    """
    Analiza el HTML de la página de resultados de SUNAT, extrae los campos
    del contribuyente y genera un HTML profesional para el reporte PDF.
    """

    CAMPOS = [
        "Número de RUC",
        "Tipo Contribuyente",
        "Nombre Comercial",
        "Fecha de Inscripción",
        "Fecha de Inicio de Actividades",
        "Estado del Contribuyente",
        "Condición del Contribuyente",
        "Domicilio Fiscal",
        "Sistema Emisión de Comprobante",
        "Actividad Comercio Exterior",
        "Sistema Contabilidad",
        "Emisor electrónico desde",
    ]

    def extraer(self, html: str) -> dict:
        """
        Extrae los datos del contribuyente desde el HTML plano.

        Args:
            html: Código HTML completo de la página de resultados.

        Returns:
            dict: Diccionario campo → valor con los datos extraídos.
        """
        datos = {}

        for campo in self.CAMPOS:
            valor = self._extraer_campo(html, campo)
            if valor:
                datos[campo] = valor

        # Extraer actividades económicas
        actividades = self._extraer_actividades(html)
        if actividades:
            datos["Actividades Económicas"] = actividades

        return datos

    def _extraer_campo(self, html: str, campo: str) -> str:
        """
        Busca un campo en el HTML usando el patrón real de SUNAT:

          <h4>CAMPO:</h4>
          ...
          <h4 o p>VALOR</h4 o p>

        El label está en .col-sm-5 y el valor en .col-sm-7 dentro del mismo
        .list-group-item.
        """
        # Escapar el campo para usarlo en regex
        campo_esc = re.escape(campo)

        # Patrón: encuentra el label y luego captura el valor en el hermano
        patron = (
            r'<h4[^>]*class="list-group-item-heading"[^>]*>'
            + campo_esc + r'[:\s]*</h4>\s*</div>\s*'
            r'<div class="col-sm-7">\s*'
            r'<(h4|p)[^>]*>(.*?)</\1>'
        )
        match = re.search(patron, html, re.IGNORECASE | re.DOTALL)
        if match:
            valor = match.group(2).strip()
            valor = re.sub(r'\s+', ' ', valor)
            return valor

        # Fallback: buscar en texto plano
        patron2 = campo_esc + r'[:\s]*\n\s*([^\n<]+)'
        match2 = re.search(patron2, html, re.IGNORECASE)
        if match2:
            valor = match2.group(1).strip()
            valor = re.sub(r'\s+', ' ', valor)
            return valor

        return ""

    def _extraer_actividades(self, html: str) -> list:
        """
        Extrae la lista de actividades económicas del HTML de SUNAT.
        """
        actividades = []
        campo = "Actividad(es) Económica(s)"
        campo_esc = re.escape(campo)

        patron = (
            r'<h4[^>]*class="list-group-item-heading"[^>]*>'
            + campo_esc + r'[:\s]*</h4>\s*</div>\s*'
            r'<div class="col-sm-7">\s*'
            r'<(h4|p)[^>]*>(.*?)</\1>'
        )
        match = re.search(patron, html, re.IGNORECASE | re.DOTALL)
        if match:
            bloque = match.group(2)
            actividades = [
                re.sub(r'\s+', ' ', a.strip())
                for a in bloque.split("<br") if a.strip()
            ]
        return actividades

    def generar_reporte_html(self, datos: dict) -> str:
        """
        Genera un HTML profesional con los datos del contribuyente,
        listo para convertir a PDF.

        Args:
            datos: Diccionario campo → valor extraído de SUNAT.

        Returns:
            str: HTML completo del reporte.
        """
        ruc = datos.get("Número de RUC", "---")
        razon_social = ""
        if " - " in ruc:
            partes = ruc.split(" - ", 1)
            ruc_num = partes[0].strip()
            razon_social = partes[1].strip()
        else:
            ruc_num = ruc

        # Construir filas de la tabla
        filas = ""
        for campo in self.CAMPOS:
            if campo in datos:
                valor = datos[campo]
                # Para el RUC mostrar solo el número en la tabla
                if campo == "Número de RUC":
                    valor = ruc_num
                filas += f"""
            <tr>
                <td class="label">{campo}</td>
                <td class="valor">{self._escapar_html(valor)}</td>
            </tr>"""

        # Actividades económicas
        if "Actividades Económicas" in datos:
            acts = datos["Actividades Económicas"]
            if isinstance(acts, list):
                acts = "<br>".join(acts)
            filas += f"""
            <tr>
                <td class="label">Actividades Económicas</td>
                <td class="valor">{acts}</td>
            </tr>"""

        fecha_reporte = datetime.now().strftime("%d/%m/%Y %H:%M")

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte SUNAT - {self._escapar_html(razon_social or ruc_num)}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', Arial, sans-serif;
        padding: 30px;
        color: #333;
    }}
    .header {{
        border-bottom: 3px solid #003366;
        padding-bottom: 15px;
        margin-bottom: 25px;
    }}
    .header h1 {{
        color: #003366;
        font-size: 22px;
        margin-bottom: 5px;
    }}
    .header .subtitle {{
        color: #666;
        font-size: 14px;
    }}
    .header .razon-social {{
        color: #003366;
        font-size: 18px;
        font-weight: bold;
        margin-top: 8px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }}
    tr {{
        border-bottom: 1px solid #e0e0e0;
    }}
    td {{
        padding: 10px 12px;
        vertical-align: top;
        font-size: 13px;
    }}
    td.label {{
        width: 35%;
        font-weight: 600;
        color: #003366;
        background: #f5f8fc;
    }}
    td.valor {{
        width: 65%;
        color: #222;
    }}
    .footer {{
        margin-top: 30px;
        padding-top: 15px;
        border-top: 2px solid #003366;
        font-size: 11px;
        color: #888;
        text-align: center;
    }}
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }}
    .badge-activo {{ background: #d4edda; color: #155724; }}
    .badge-habido {{ background: #cce5ff; color: #004085; }}
</style>
</head>
<body>
    <div class="header">
        <h1>Plataforma de Consulta Masiva - SUNAT</h1>
        <div class="subtitle">Extracto Oficial Informativo del Contribuyente</div>
        <div class="razon-social">{self._escapar_html(razon_social or "---")}</div>
    </div>
    <table>
        {filas}
    </table>
    <div class="footer">
        Fecha de consulta: {fecha_reporte} &nbsp;|&nbsp; ID de Reporte: VR-{ruc_num}<br>
        &copy; {datetime.now().year} SUNAT - Superintendencia Nacional de Aduanas y de Administración Tributaria
    </div>
</body>
</html>"""
        return html

    @staticmethod
    def _escapar_html(texto: str) -> str:
        """Escapa caracteres HTML básicos."""
        texto = str(texto)
        texto = texto.replace("&", "&amp;")
        texto = texto.replace("<", "&lt;")
        texto = texto.replace(">", "&gt;")
        texto = texto.replace('"', "&quot;")
        return texto
