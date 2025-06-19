"""
Módulo para registrar todos los reconocedores personalizados con Presidio.
Este archivo centraliza el registro de reconocedores personalizados para facilitar
su uso en el servicio de Presidio.
"""

from typing import List
from presidio_analyzer import RecognizerRegistry, PatternRecognizer

# Importar los reconocedores personalizados (corrigiendo rutas)
from src.recognizers.colombian_id_recognizer import ColombianIDRecognizer 
from src.recognizers.colombian_location_recognizer import ColombianLocationRecognizer
from src.utils.logger import setup_logger

# Utilizar el logger configurado en el módulo logger
logger = setup_logger("presidio_recognizers")

def create_colombian_id_recognizer() -> PatternRecognizer:
    """
    Crea y devuelve una instancia del reconocedor de documentos colombianos.
    
    Returns:
        PatternRecognizer: Instancia del reconocedor de documentos colombianos
    """
    try:
        return ColombianIDRecognizer()
    except Exception as e:
        logger.error(f"Error al crear el reconocedor de documentos colombianos: {str(e)}")
        raise

def create_colombian_location_recognizer() -> PatternRecognizer:
    """
    Crea y devuelve una instancia del reconocedor de ubicaciones colombianas.
    
    Returns:
        PatternRecognizer: Instancia del reconocedor de ubicaciones colombianas
    """
    try:
        return ColombianLocationRecognizer(supported_language="es")
    except Exception as e:
        logger.error(f"Error al crear el reconocedor de ubicaciones colombianas: {str(e)}")
        return None  # Devolver None permite que el sistema continúe si este reconocedor falla

def get_all_custom_recognizers() -> List[PatternRecognizer]:
    """
    Crea y devuelve una lista con todos los reconocedores personalizados.
    
    Returns:
        List[PatternRecognizer]: Lista de todos los reconocedores personalizados
    """
    recognizers = []
    
    # Agregar reconocedor de documentos colombianos
    try:
        colombian_id_recognizer = create_colombian_id_recognizer()
        recognizers.append(colombian_id_recognizer)
        logger.info("Reconocedor de documentos colombianos creado correctamente")
    except Exception as e:
        logger.error(f"No se pudo crear el reconocedor de documentos colombianos: {str(e)}")
    
    # Agregar reconocedor de ubicaciones colombianas
    try:
        location_recognizer = create_colombian_location_recognizer()
        if location_recognizer:
            recognizers.append(location_recognizer)
            logger.info("Reconocedor de ubicaciones colombianas creado correctamente")
    except Exception as e:
        logger.error(f"No se pudo crear el reconocedor de ubicaciones colombianas: {str(e)}")
    
    return recognizers

def register_custom_recognizers(registry: RecognizerRegistry, language: str = "es") -> None:
    """
    Registra todos los reconocedores personalizados en el registro de Presidio.
    
    Args:
        registry (RecognizerRegistry): El registro donde se añadirán los reconocedores
        language (str, optional): Idioma para el que se registrarán los reconocedores. 
                                Por defecto es "es" (español).
    """
    # Cargar reconocedores predefinidos para el idioma
    registry.load_predefined_recognizers(languages=[language])
    
    # Registrar directamente el reconocedor de documentos colombianos
    try:
        colombian_id_recognizer = ColombianIDRecognizer()
        registry.add_recognizer(colombian_id_recognizer)
        logger.info(f"Reconocedor de documentos colombianos registrado correctamente (idioma: {language})")
    except Exception as e:
        logger.error(f"Error al registrar el reconocedor de documentos colombianos: {str(e)}")
    
    # Registrar el reconocedor de ubicaciones colombianas
    try:
        colombian_location_recognizer = ColombianLocationRecognizer(supported_language=language)
        registry.add_recognizer(colombian_location_recognizer)
        logger.info(f"Reconocedor de ubicaciones colombianas registrado correctamente (idioma: {language})")
    except Exception as e:
        logger.error(f"Error al registrar el reconocedor de ubicaciones colombianas: {str(e)}")
    
    # Verificar si hay reconocedores registrados
    if not registry.recognizers:
        logger.error("¡ALERTA! No se registraron reconocedores. El sistema puede no funcionar correctamente.")
    else:
        logger.info(f"Total de reconocedores registrados: {len(registry.recognizers)}")
        
        # Listar los reconocedores registrados para depuración
        recognizer_names = [f"{r.name} ({getattr(r, 'supported_entity', 'N/A')})" for r in registry.recognizers]
        logger.debug(f"Reconocedores registrados: {', '.join(recognizer_names)}")
