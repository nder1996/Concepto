"""
Configuración de motores de análisis de lenguaje para Presidio.
Define la configuración específica de los analizadores y modelos de lenguaje para los idiomas soportados.
"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.recognizers.registry import register_custom_recognizers
from src.utils.logger import setup_logger
import importlib.util

# Configuraciones de idioma para los modelos NLP
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

# Idiomas soportados
SUPPORTED_LANGUAGES = list(LANGUAGE_MODELS.keys())
DEFAULT_LANGUAGE = "es"  # Español como idioma predeterminado

def is_spacy_model_installed(model_name):
    """
    Verifica si un modelo de spaCy está instalado.
    
    Args:
        model_name (str): Nombre del modelo de spaCy.
        
    Returns:
        bool: True si el modelo está instalado, False en caso contrario.
    """
    return importlib.util.find_spec(model_name) is not None

def initialize_language_analyzers():
    """
    Inicializa y configura los analizadores para los diferentes idiomas soportados.
    
    Returns:
        dict: Diccionario con los analizadores configurados por idioma.
    """
    logger = setup_logger("LanguageConfig")
    analyzers = {}
    
    logger.info("Inicializando analizadores para diferentes idiomas...")
    
    try:
        # Inicializar analizadores para cada idioma configurado
        for lang_code, lang_config in LANGUAGE_MODELS.items():
            try:
                model_name = lang_config['model_name']
                
                # Verificar si el modelo está instalado
                if not is_spacy_model_installed(model_name):
                    logger.warning(f"El modelo {model_name} para {lang_code} no está instalado.")
                    logger.warning(f"Ejecute: python -m spacy download {model_name}")
                    # Usar configuración básica sin modelo específico
                    registry = RecognizerRegistry()
                    register_custom_recognizers(registry, language=lang_code)
                    analyzers[lang_code] = AnalyzerEngine(registry=registry)
                    continue
                
                # Intentar cargar el modelo específico para el idioma
                logger.info(f"Cargando modelo para {lang_code} ({lang_config['model_name']})...")
                
                provider = NlpEngineProvider(nlp_configuration=lang_config['config'])
                nlp_engine = provider.create_engine()
                
                # Crear registro de reconocedores
                registry = RecognizerRegistry()
                register_custom_recognizers(registry, language=lang_code)
                
                # Crear analizador con el motor NLP específico
                analyzers[lang_code] = AnalyzerEngine(
                    registry=registry,
                    nlp_engine=nlp_engine
                )
                logger.info(f"Motor NLP para {lang_code} inicializado correctamente.")
                
            except Exception as e:
                logger.error(f"Error al cargar el modelo para {lang_code}: {str(e)}")
                logger.warning(f"Usando configuración de respaldo para {lang_code}...")
                  # Si falla, usamos un registro normal sin modelo específico
                registry = RecognizerRegistry()
                register_custom_recognizers(registry, language=lang_code)
                analyzers[lang_code] = AnalyzerEngine(registry=registry)
        
        # Verificar que tengamos al menos un analizador
        if not analyzers:
            logger.warning("¡No se pudo inicializar ningún analizador! Creando un analizador básico para el idioma predeterminado.")
            registry = RecognizerRegistry()
            register_custom_recognizers(registry, language=DEFAULT_LANGUAGE)
            analyzers[DEFAULT_LANGUAGE] = AnalyzerEngine(registry=registry)
            
        logger.info("Motores de análisis inicializados correctamente.")
        
    except Exception as e:
        logger.error(f"Error al inicializar los motores de análisis: {str(e)}")
        # No relanzo la excepción para evitar que la aplicación falle por completo
        # En su lugar, creamos un analizador básico para el idioma predeterminado
        try:
            registry = RecognizerRegistry()
            register_custom_recognizers(registry, language=DEFAULT_LANGUAGE)
            analyzers[DEFAULT_LANGUAGE] = AnalyzerEngine(registry=registry)
            logger.info(f"Se creó un analizador básico de respaldo para {DEFAULT_LANGUAGE}.")
        except Exception as inner_e:
            logger.error(f"Error crítico al crear analizador de respaldo: {str(inner_e)}")
        
    return analyzers
