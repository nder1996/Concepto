"""
Configuración simplificada de motores de análisis de lenguaje para Presidio.
"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.recognizers.colombian_id_recognizer import ColombianIDRecognizer
from src.recognizers.colombian_location_recognizer import ColombianLocationRecognizer
import importlib.util
import logging

# Configuraciones de idioma
LANGUAGE_MODELS = {
    "es": {
        "model_name": "es_core_news_md",
        "config": {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "es", "model_name": "es_core_news_md"}]
        }
    },
    "en": {
        "model_name": "en_core_web_lg",
        "config": {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]
        }
    }
}

SUPPORTED_LANGUAGES = list(LANGUAGE_MODELS.keys())
DEFAULT_LANGUAGE = "es"

logger = logging.getLogger(__name__)

def is_spacy_model_installed(model_name):
    """Verifica si un modelo de spaCy está instalado"""
    return importlib.util.find_spec(model_name) is not None

def initialize_language_analyzers():
    """Inicializa analizadores para cada idioma"""
    analyzers = {}
    
    for lang_code, lang_config in LANGUAGE_MODELS.items():
        try:
            analyzers[lang_code] = _create_analyzer(lang_code, lang_config)
        except Exception as e:
            logger.error(f"Error creando analizador para {lang_code}: {e}")
            analyzers[lang_code] = _create_fallback_analyzer(lang_code)
    
    # Asegurar que al menos tengamos el idioma por defecto
    if not analyzers:
        analyzers[DEFAULT_LANGUAGE] = _create_fallback_analyzer(DEFAULT_LANGUAGE)
    
    return analyzers

def _create_analyzer(lang_code, lang_config):
    """Crea un analizador con modelo NLP específico"""
    model_name = lang_config['model_name']
    
    # Crear registro con reconocedores
    registry = RecognizerRegistry()
    _register_recognizers(registry, lang_code)
    
    # Si el modelo está disponible, usar configuración completa
    if is_spacy_model_installed(model_name):
        provider = NlpEngineProvider(nlp_configuration=lang_config['config'])
        nlp_engine = provider.create_engine()
        return AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
    else:
        logger.warning(f"Modelo {model_name} no instalado. Usando configuración básica.")
        return AnalyzerEngine(registry=registry)

def _create_fallback_analyzer(lang_code):
    """Crea un analizador básico de respaldo"""
    registry = RecognizerRegistry()
    _register_recognizers(registry, lang_code)
    return AnalyzerEngine(registry=registry)

def _register_recognizers(registry, language):
    """Registra reconocedores predefinidos y personalizados"""
    # Cargar reconocedores predefinidos
    registry.load_predefined_recognizers(languages=[language])
    
    # Agregar reconocedores personalizados solo para español
    if language == "es":
        try:
            registry.add_recognizer(ColombianIDRecognizer())
            registry.add_recognizer(ColombianLocationRecognizer(supported_language=language))
        except Exception as e:
            logger.error(f"Error registrando reconocedores personalizados: {e}")

# Función duplicada para compatibilidad (se puede remover si no se usa en otro lugar)
def register_custom_recognizers(registry: RecognizerRegistry, language: str = "es") -> None:
    """Función de compatibilidad - usa _register_recognizers internamente"""
    _register_recognizers(registry, language)