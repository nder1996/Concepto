"""
Configuración de entidades para la detección con Presidio.
Define las entidades objetivo y sus umbrales de confianza para español e inglés.
"""

# Entidades específicas a considerar
TARGET_ENTITIES = [
    #"PERSON", 
    "PHONE_NUMBER", 
    "EMAIL_ADDRESS",
    "COLOMBIAN_ID_DOC",  # Cédulas y otros documentos de identidad colombianos
    #"COLOMBIAN_LOCATION",  # Ubicaciones específicas de Colombia usando DIVIPOLA
]

# Umbrales específicos para cada tipo de entidad - configuración para inglés
ENTITY_THRESHOLDS_EN = {
    #"PERSON": 0.1,  # Umbral bajo para capturar más candidatos
    "PHONE_NUMBER": 0.2,  # Umbral bajo para mejorar detección
    "EMAIL_ADDRESS": 0.6,  # Ajustado para mejor precisión
    "COLOMBIAN_ID_DOC": 0.1,  # Reducido para capturar más documentos de identidad
    #"COLOMBIAN_LOCATION": 0.1,  # Umbral para ubicaciones específicas de Colombia usando DIVIPOLA
}

# Umbrales específicos para cada tipo de entidad - configuración para español
ENTITY_THRESHOLDS_ES = {
    #"PERSON": 0.1,  # Umbral bajo para capturar más candidatos
    "PHONE_NUMBER": 0.2,  # Más alto para evitar falsos positivos con cédulas
    "EMAIL_ADDRESS": 0.6,  # Ajustado para mejor precisión
    "COLOMBIAN_ID_DOC": 0.1,  # Reducido para mejorar la detección en español
    #"COLOMBIAN_LOCATION": 0.1,  # Umbral específico para ubicaciones colombianas usando DIVIPOLA
}

# Diccionario de umbrales por idioma
THRESHOLDS_BY_LANGUAGE = {
    "en": ENTITY_THRESHOLDS_EN,
    "es": ENTITY_THRESHOLDS_ES,
}

# Por compatibilidad con código existente - Configurado para usar español como predeterminado
ENTITY_THRESHOLDS = ENTITY_THRESHOLDS_ES
