"""
Utilidades para los reconocedores personalizados
"""
import logging
from presidio_analyzer import RecognizerRegistry

def log_active_recognizers(logger=None):
    """
    Muestra los reconocedores activos en el registro predeterminado de Presidio.
    Útil para depurar qué reconocedores están disponibles.
    
    Args:
        logger: Logger opcional para registrar la información
    """
    if logger is None:
        logger = logging.getLogger("custom_recognizers")
    
    # Crear un registro nuevo para verificar qué reconocedores están disponibles
    try:
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=["es", "en"])
        
        # Importar y registrar reconocedores personalizados
        from src.recognizers.registry import register_custom_recognizers
        register_custom_recognizers(registry, language="es")
        
        # Listar reconocedores
        recognizers = registry.recognizers
        logger.info(f"Total de reconocedores activos: {len(recognizers)}")
        
        # Mostrar detalles de cada reconocedor
        for i, recognizer in enumerate(recognizers, 1):
            try:
                name = getattr(recognizer, 'name', 'sin nombre')
                entity = getattr(recognizer, 'supported_entity', 'N/A')
                language = getattr(recognizer, 'supported_language', 'N/A')
                
                logger.info(f"{i}. Reconocedor: {name}, Entidad: {entity}, Idioma: {language}")
            except Exception as e:
                logger.error(f"Error al obtener información del reconocedor #{i}: {e}")
                
    except Exception as e:
        logger.error(f"Error al verificar reconocedores activos: {e}")
