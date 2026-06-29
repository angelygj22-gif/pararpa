# =============================================================================
# Módulo: notificador.py
# Propósito: Enviar un correo electrónico al administrador al finalizar
#            el proceso masivo, adjuntando el reporte de resultados.
# Ciclo de vida: Fase 5 - Notificación
# =============================================================================

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


class Notificador:
    """
    Cliente SMTP para enviar correos electrónicos con adjunto opcional.
    Soporta TLS y autenticación contra servidores como Office 365.
    """

    def __init__(self, config_email: dict):
        """
        Toma la configuración de email desde el config.json.

        Args:
            config_email: Diccionario con claves:
                Servidor, Puerto, Usuario, Password, Destinatario, UsarSSL
        """
        self.servidor = config_email.get("Servidor", "smtp.office365.com")
        self.puerto = config_email.get("Puerto", 587)
        self.usuario = config_email.get("Usuario", "")
        self.password = config_email.get("Password", "")
        self.destinatario = config_email.get("Destinatario", "")
        self.usar_ssl = config_email.get("UsarSSL", True)

    def enviar(self, asunto: str, cuerpo: str, archivo_adjunto: str = None, archivos_extra: list = None) -> bool:
        """
        Construye y envía el correo.

        Args:
            asunto: Línea de asunto del correo.
            cuerpo: Cuerpo del mensaje en texto plano.
            archivo_adjunto: Ruta opcional de un archivo para adjuntar.

        Returns:
            bool: True si el envío fue exitoso, False en caso contrario.
        """
        # Si no hay credenciales configuradas, se omite el envío
        if not self.usuario or not self.password:
            print("Credenciales de email no configuradas. Omitiendo envío.")
            return False

        # Construir el mensaje multipart
        msg = MIMEMultipart()
        msg["From"] = self.usuario
        msg["To"] = self.destinatario
        msg["Subject"] = asunto

        # Adjuntar el cuerpo del mensaje
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        # Adjuntar archivos
        archivos = []
        if archivo_adjunto:
            archivos.append(archivo_adjunto)
        if archivos_extra:
            archivos.extend(archivos_extra)

        for ruta in archivos:
            if ruta and os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    parte = MIMEBase("application", "octet-stream")
                    parte.set_payload(f.read())
                    encoders.encode_base64(parte)
                    parte.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(ruta)}"
                    )
                    msg.attach(parte)

        # Enviar el correo vía SMTP con TLS
        try:
            with smtplib.SMTP(self.servidor, self.puerto) as server:
                server.starttls()
                server.login(self.usuario, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error al enviar correo: {e}")
            return False
