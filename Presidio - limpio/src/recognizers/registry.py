"""
Registro simplificado de reconocedores personalizados para Presidio.
"""

from presidio_analyzer import RecognizerRegistry
from src.recognizers.colombian_id_recognizer import ColombianIDRecognizer
from src.recognizers.colombian_location_recognizer import ColombianLocationRecognizer
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def register_custom_recognizers(registry: RecognizerRegistry, language: str = "es") -> None:
    """
    Registra reconocedores personalizados en el registro de Presidio.
    
    Args:
        registry: El registro donde se añadirán los reconocedores
        language: Idioma para los reconocedores (default: "es")
    """
    # Solo agregar reconocedores personalizados para español
    if language != "es":
        return
    
    recognizers = [
        ColombianIDRecognizer(),
        ColombianLocationRecognizer(supported_language=language)
    ]
    
    # Registrar reconocedores personalizados
    logger.info("=== RECONOCEDORES PERSONALIZADOS REGISTRADOS ===")
    for recognizer in recognizers:
        try:
            registry.add_recognizer(recognizer)
            entity = getattr(recognizer, 'supported_entity', 'N/A')
            logger.info(f"✅ {recognizer.__class__.__name__} -> Entidad: {entity}")
        except Exception as e:
            logger.error(f"❌ Error registrando {recognizer.__class__.__name__}: {e}")
    
    # Mostrar entidades activas
    from src.config.entity_config import TARGET_ENTITIES
    logger.info("=== ENTIDADES OBJETIVO ACTIVAS ===")
    for entity in TARGET_ENTITIES:
        logger.info(f"🎯 {entity}")
    logger.info("=" * 50)