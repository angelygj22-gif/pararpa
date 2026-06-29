import re


class ExtractorDatos:
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
        datos = {}
        for campo in self.CAMPOS:
            valor = self._extraer_campo(html, campo)
            if valor:
                datos[campo] = valor
        actividades = self._extraer_actividades(html)
        if actividades:
            datos["Actividades Económicas"] = actividades
        return datos

    def _extraer_campo(self, html: str, campo: str) -> str:
        campo_esc = re.escape(campo)
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
        patron2 = campo_esc + r'[:\s]*\n\s*([^\n<]+)'
        match2 = re.search(patron2, html, re.IGNORECASE)
        if match2:
            valor = match2.group(1).strip()
            valor = re.sub(r'\s+', ' ', valor)
            return valor
        return ""

    def _extraer_actividades(self, html: str) -> list:
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
