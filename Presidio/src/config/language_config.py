"""
Configuración de motores de análisis de lenguaje para Presidio.
Define la configuración específica de los analizadores y modelos de lenguaje para los idiomas soportados.
"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.utils.custom_recognizers import register_custom_recognizers
from src.utils.logger import setup_logger

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
                # Intentar cargar el modelo específico para el idioma
                logger.info(f"Cargando modelo para {lang_code} ({lang_config['model_name']})...")
                
                provider = NlpEngineProvider(nlp_configuration=lang_config['config'])
                nlp_engine = provider.create_engine()
                
                # Crear registro de reconocedores
                registry = RecognizerRegistry()
                register_custom_recognizers(registry)
                
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
                register_custom_recognizers(registry)
                analyzers[lang_code] = AnalyzerEngine(registry=registry)
        
        logger.info("Motores de análisis inicializados correctamente para todos los idiomas.")
        
    except Exception as e:
        logger.error(f"Error al inicializar los motores de análisis: {str(e)}")
        raise
        
    return analyzers
