"""
Configuración de entidades para la detección con Presidio.
Define las entidades objetivo y sus umbrales de confianza para español e inglés.
"""

# Entidades específicas a considerar
TARGET_ENTITIES = [
    "PERSON", 
    "PHONE_NUMBER", 
    "EMAIL_ADDRESS",
]

# Umbrales específicos para cada tipo de entidad - configuración para inglés
ENTITY_THRESHOLDS_EN = {
    "PERSON": 0.1,  # Umbral bajo para capturar más candidatos
    "PHONE_NUMBER": 0.3,  # Umbral bajo para mejorar detección
    "EMAIL_ADDRESS": 0.6,  # Ajustado para mejor precisión
}

# Umbrales específicos para cada tipo de entidad - configuración para español
ENTITY_THRESHOLDS_ES = {
    "PERSON": 0.1,  # Umbral bajo para capturar más candidatos
    "PHONE_NUMBER": 0.3,  # Más bajo para detectar diferentes formatos
    "EMAIL_ADDRESS": 0.6,  # Ajustado para mejor precisión
}

# Diccionario de umbrales por idioma
THRESHOLDS_BY_LANGUAGE = {
    "en": ENTITY_THRESHOLDS_EN,
    "es": ENTITY_THRESHOLDS_ES,
}

# Por compatibilidad con código existente - Configurado para usar español como predeterminado
ENTITY_THRESHOLDS = ENTITY_THRESHOLDS_ES
