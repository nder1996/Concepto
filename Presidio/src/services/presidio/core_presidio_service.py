"""
Servicio Core de Presidio.
Este módulo proporciona la funcionalidad básica de detección y anonimización de entidades
utilizando Microsoft Presidio. Esta implementación es considerada el núcleo del sistema
y no debe ser modificada frecuentemente.
"""

from typing import List, Dict, Any, Optional
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
except ImportError:
    # Para manejar posibles errores de importación en caso de que Presidio no esté instalado
    raise ImportError("No se pudieron importar los módulos de Microsoft Presidio. Asegúrate de que estén instalados correctamente.")
    
from src.utils.logger import setup_logger
from src.config.settings import (
    ENTITY_THRESHOLDS, 
    SUPPORTED_ENTITY_TYPES,
    ENTITY_REPLACEMENT_LABELS,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    FLAIR_CONFIDENCE_THRESHOLD
)


class CorePresidioService:
    """
    Servicio core de Presidio que implementa las funcionalidades básicas de análisis
    y anonimización de texto. Esta clase es considerada el núcleo del sistema
    y contiene métodos que no deberían cambiar frecuentemente.
    """
    
    def __init__(self, flair_service=None):
        """
        Inicializa el servicio core de Presidio con motores de análisis y anonimización.
        
        Args:
            flair_service: Servicio opcional de Flair para validación adicional
        """
        self.logger = setup_logger("CorePresidioService")
        
        # Inicializar el registro de reconocedores
        self.logger.info("Configurando reconocedores...")
        self.registry = RecognizerRegistry()
        self.registry.load_predefined_recognizers()
        
        # Registrar reconocedores personalizados
        self._register_custom_recognizers()
        
        # Inicializar motor analizador con los reconocedores registrados
        self.analyzer = AnalyzerEngine(registry=self.registry)
        self.anonymizer = AnonymizerEngine()
        
        # Configuración centralizada
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        self.target_entities = SUPPORTED_ENTITY_TYPES
        self.replacement_labels = ENTITY_REPLACEMENT_LABELS
        
        # Integración con Flair (opcional)
        self.flair_service = flair_service
        self.flair_disponible = flair_service is not None
        self.logger.info(f"Servicio inicializado. Flair: {'Disponible' if self.flair_disponible else 'No disponible'}")

    def _register_custom_recognizers(self):
        """Registra los reconocedores personalizados"""
        try:
            from src.services.presidio.recognizers import EmailRecognizer, PhoneRecognizer, ColombianIDRecognizer
            
            self.registry.add_recognizer(EmailRecognizer())
            self.registry.add_recognizer(PhoneRecognizer())
            self.registry.add_recognizer(ColombianIDRecognizer())
            self.logger.info("Reconocedores personalizados registrados correctamente")
        except Exception as e:
            self.logger.error(f"Error al registrar reconocedores personalizados: {str(e)}")

    def get_service_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del servicio

        Returns:
            Dict con información sobre el estado del servicio
        """
        return {
            "presidio_service": "active",
            "flair_service": "active" if self.flair_disponible else "inactive",
            "supported_languages": self.supported_languages,
            "default_language": self.default_language,
            "supported_entity_types": self.target_entities,
            "version": "3.0",
        }

    def analyze_text(self, text: str, language: str = None, entities: List[str] = None) -> List[Dict[str, Any]]:
        """
        Analiza un texto para detectar entidades PII, usando Flair para validar
        entidades PERSON cuando sea necesario.

        Args:
            text: Texto a analizar
            language: Idioma del texto ('es', 'en')
            entities: Lista de tipos de entidades a buscar (opcional)

        Returns:
            Lista de entidades encontradas con detalles
        """
        if not text or len(text.strip()) == 0:
            self.logger.warning("Texto vacío enviado para análisis")
            return []

        # Validar y establecer idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            language = self.default_language
            self.logger.warning(f"Idioma no soportado. Usando: {language}")

        self.logger.info(f"Analizando texto ({len(text)} caracteres)")
        
        try:
            # Realizar análisis con Presidio
            analyzer_results = self.analyzer.analyze(
                text=text, 
                language=language,
                entities=entities
            )
            
            # Obtener umbrales de confianza según idioma
            thresholds = ENTITY_THRESHOLDS.get(language, ENTITY_THRESHOLDS[DEFAULT_LANGUAGE])
            default_threshold = thresholds.get('DEFAULT', 0.70)
            
            # Procesar y filtrar resultados
            filtered_results = []
            for result in analyzer_results:
                entity_type = result.entity_type
                entity_text = text[result.start:result.end]
                threshold = thresholds.get(entity_type, default_threshold)
                
                # Para PERSON, usar Flair si está disponible y la confianza no es muy alta
                if entity_type == "PERSON" and self.flair_disponible and result.score < 0.85:
                    # Validar con Flair - solo carga el modelo si es la primera validación
                    is_valid = self.flair_service.validate_entity(entity_text, "PERSON")
                    
                    if is_valid:
                        # Si Flair valida, aumentar la confianza
                        result.score = min(result.score + 0.2, 1.0)
                    else:
                        # Si Flair rechaza y la confianza es baja, descartar
                        if result.score < threshold:
                            continue
                
                # Solo incluir resultados que superen el umbral
                if result.score >= threshold:
                    entity_dict = {
                        'start': result.start,
                        'end': result.end,
                        'score': result.score,
                        'entity_type': entity_type,
                        'text': entity_text
                    }
                    
                    # Agregar detalles si están disponibles
                    if hasattr(result, 'analysis_explanation') and result.analysis_explanation:
                        entity_dict['analysis_explanation'] = result.analysis_explanation
                        
                    filtered_results.append(entity_dict)
            
            self.logger.info(f"Entidades encontradas: {len(filtered_results)}")
            return filtered_results

        except Exception as e:
            self.logger.error(f"Error durante análisis: {str(e)}")
            return []

    def anonymize_text(self, text: str, language: str = None, entities: List[str] = None) -> Dict[str, Any]:
        """
        Anonimiza un texto utilizando los resultados del análisis

        Args:
            text: Texto a anonimizar
            language: Idioma del texto
            entities: Tipos de entidades a anonimizar (opcional)

        Returns:
            Dict con texto anonimizado y estadísticas
        """
        if not text or len(text.strip()) == 0:
            self.logger.warning("Texto vacío enviado para anonimización")
            return {"text": "", "items": []}

        # Analizar el texto primero para encontrar entidades
        results = self.analyze_text(text, language, entities)

        if not results:
            self.logger.info("No se encontraron entidades para anonimizar")
            return {"text": text, "items": []}

        # Convertir resultados a formato reconocido por Presidio Anonymizer
        analyzer_results = []

        for entity_dict in results:
            # Crear un ResultRecognizer simplificado
            result = {
                "start": entity_dict["start"],
                "end": entity_dict["end"],
                "score": entity_dict["score"],
                "entity_type": entity_dict["entity_type"],
            }
            analyzer_results.append(result)
            
        # Configurar operadores de anonimización según el tipo de entidad
        operators = {
            entity_type: OperatorConfig("replace", {"new_value": label})
            for entity_type, label in self.replacement_labels.items()
        }

        # Anonimizar el texto
        try:
            anonymize_result = self.anonymizer.anonymize(
                text=text, analyzer_results=analyzer_results, operators=operators
            )

            self.logger.info(f"Texto anonimizado. Entidades reemplazadas: {len(results)}")
            return {
                "text": anonymize_result.text,
                "items": [dict(item) for item in anonymize_result.items],
            }
        except Exception as e:
            self.logger.error(f"Error durante anonimización: {str(e)}")
            return {"text": text, "items": [], "error": str(e)}