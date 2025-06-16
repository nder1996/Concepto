"""
Configuración común para toda la aplicación.
Este módulo proporciona constantes y configuraciones para ser compartidas
entre los diferentes componentes de la aplicación.
"""

# Idiomas soportados
SUPPORTED_LANGUAGES = ['en', 'es']
DEFAULT_LANGUAGE = 'es'

# Nombres descriptivos de idiomas
LANGUAGE_NAMES = {
    'en': 'inglés', 
    'es': 'español'
}

# Umbrales de confianza para entidades por idioma
ENTITY_THRESHOLDS = {
    'es': {
        'PERSON': 0.60,
        'LOCATION': 0.60,
        'EMAIL_ADDRESS': 0.70,
        'PHONE_NUMBER': 0.70,
        'CREDIT_CARD': 0.70,
        'COLOMBIAN_ID': 0.85,
        'IBAN_CODE': 0.70, 
        'DATE_TIME': 0.60,
        'NRP': 0.60,  # Nombres, Razones sociales y Patentes
        'DEFAULT': 0.65
    },
    'en': {
        'PERSON': 0.65,
        'LOCATION': 0.65,
        'EMAIL_ADDRESS': 0.75,
        'PHONE_NUMBER': 0.75,
        'CREDIT_CARD': 0.75,
        'IBAN_CODE': 0.75,
        'DATE_TIME': 0.60,
        'NRP': 0.65,  # Nombres, Razones sociales y Patentes
        'DEFAULT': 0.70
    }
}

# Configuración de modelos de spaCy por idioma
SPACY_MODELS = {
    'es': 'es_core_news_sm',
    'en': 'en_core_web_sm'
}

# Configuración del modelo Flair
FLAIR_MODEL = 'flair/ner-spanish-large'
FLAIR_CONFIDENCE_THRESHOLD = 0.90

# Tipos de entidades soportadas por el sistema
SUPPORTED_ENTITY_TYPES = [
    "PERSON",
    "LOCATION",
    "ORGANIZATION",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "CO_ID_NUMBER",
    "IBAN_CODE",
    "DATE_TIME",
    "URL",
    "IP_ADDRESS",
    "NRP",
    "US_PASSPORT",
    "US_SSN",
    "US_DRIVER_LICENSE"
]

# Configuración de las etiquetas de reemplazo para la anonimización
ENTITY_REPLACEMENT_LABELS = {
    "PERSON": "[NOMBRE]",
    "LOCATION": "[UBICACIÓN]",
    "ORGANIZATION": "[ORGANIZACIÓN]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[TELÉFONO]",
    "CREDIT_CARD": "[TARJETA]",
    "CO_ID_NUMBER": "[DOCUMENTO]",
    "IBAN_CODE": "[IBAN]",
    "DATE_TIME": "[FECHA]",
    "URL": "[URL]",
    "IP_ADDRESS": "[IP]",
    "NRP": "[NRP]",
    "US_PASSPORT": "[PASAPORTE]",
    "US_SSN": "[SSN]",
    "US_DRIVER_LICENSE": "[LICENCIA]"
}
