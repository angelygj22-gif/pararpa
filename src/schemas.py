def respuesta_vacia(ruc: str = "", detalle: str = "", status: str = "Error", estado: str = "NO EXISTE"):
    return {
        "ruc": ruc,
        "razon_social": "",
        "tipo_contribuyente": "",
        "nombre_comercial": "",
        "fecha_inscripcion": "",
        "fecha_inicio_actividades": "",
        "estado": estado,
        "condicion": "",
        "domicilio_fiscal": "",
        "sistema_emision": "",
        "actividad_comercio_exterior": "",
        "sistema_contabilidad": "",
        "emisor_electronico_desde": "",
        "actividades_economicas": [],
        "detalle": detalle,
        "status": status,
    }
