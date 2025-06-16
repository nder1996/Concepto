"""
Servicio Core de Presidio.
Este módulo proporciona la funcionalidad básica de detección y anonimización de entidades
utilizando Microsoft Presidio. Esta implementación es considerada el núcleo del sistema
y no debe ser modificada frecuentemente.
"""

from typing import List, Dict, Any, Optional
try:
    from presidio_analyzer import AnalyzerEngine
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
    SUPPORTED_LANGUAGES
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
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.logger = setup_logger("CorePresidioService")
        
        # Configuración centralizada
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        self.target_entities = SUPPORTED_ENTITY_TYPES
        self.replacement_labels = ENTITY_REPLACEMENT_LABELS
        
        # Integración con Flair (opcional)
        self.flair_service = flair_service
        self.flair_disponible = flair_service is not None

    def validate_person_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        """
        Valida entidades PERSON con Flair si está disponible

        Args:
            text: Texto a analizar
            language: Idioma del texto

        Returns:
            Lista de entidades PERSON validadas
        """
        if not self.flair_disponible:
            self.logger.warning(
                "Flair no está disponible para validación de personas. Usando solo Presidio"
            )
            # Analizar solo para entidades PERSON utilizando el método estándar
            analyzer_results = self.analyzer.analyze(
                text=text, 
                language=language,
                entities=["PERSON"]
            )
            
            # Filtrar por umbral
            if language not in ENTITY_THRESHOLDS:
                language = DEFAULT_LANGUAGE
            
            thresholds = ENTITY_THRESHOLDS[language]
            default_threshold = thresholds.get('DEFAULT', 0.70)
            person_threshold = thresholds.get('PERSON', default_threshold)
            
            filtered_results = []
            for result in analyzer_results:
                if result.score >= person_threshold:
                    entity_dict = {
                        'start': result.start,
                        'end': result.end,
                        'score': result.score,
                        'entity_type': result.entity_type,
                        'analysis_explanation': result.analysis_explanation,
                        'text': text[result.start:result.end]
                    }
                    filtered_results.append(entity_dict)
            
            return filtered_results

        # Si Flair está disponible, utilizar servicio de Flair para mejorar precisión
        try:
            # Obtener candidatos con Presidio con umbral bajo
            analyzer_results = self.analyzer.analyze(
                text=text, 
                language=language,
                entities=["PERSON"]
            )
            
            presidio_candidates = []
            for result in analyzer_results:
                entity_dict = {
                    'start': result.start,
                    'end': result.end,
                    'score': result.score,
                    'entity_type': result.entity_type,
                    'analysis_explanation': result.analysis_explanation,
                    'text': text[result.start:result.end]
                }
                presidio_candidates.append(entity_dict)

            # Validar con Flair
            validated_entities = []
            for entity in presidio_candidates:
                entity_text = entity["text"]
                # Validar con Flair
                is_valid = self.flair_service.validate_entity(
                    entity_text, language, "PERSON"
                )

                if is_valid:
                    validated_entities.append(entity)

            self.logger.info(
                f"Validación con Flair: {len(presidio_candidates)} candidatos, {len(validated_entities)} validados"
            )
            return validated_entities

        except Exception as e:
            self.logger.error(f"Error en validación con Flair: {str(e)}")
            # Caer en análisis estándar si hay error
            return self.analyze_text(text, language)

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
        Analiza un texto para detectar entidades PII

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
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language

        # Log simplificado con información de método y datos JSON
        import json
        payload = {"text_length": len(text), "language": language}
        if entities:
            payload["entities"] = entities
        self.logger.info(f"[analyze_text] Entrada: {json.dumps(payload)}")

        try:
            # Verificar si necesitamos validación especial para personas
            if self.flair_disponible and entities and "PERSON" in entities:
                self.logger.info("Solicitada análisis específico para entidades PERSON")
                person_entities = self.validate_person_entities(text, language)

                # Si solo se solicitaron entidades PERSON, devolver solo esas
                if len(entities) == 1:
                    return person_entities

                # Si se solicitaron más entidades, obtener el resto y combinarlas
                other_entities = [e for e in entities if e != "PERSON"]
                
                # Analizar con Presidio para el resto de entidades
                analyzer_results = self.analyzer.analyze(
                    text=text, 
                    language=language,
                    entities=other_entities
                )
                
                # Convertir resultados a diccionario
                other_results = []
                
                # Obtener umbrales para filtrado
                if language not in ENTITY_THRESHOLDS:
                    language = DEFAULT_LANGUAGE
                
                thresholds = ENTITY_THRESHOLDS[language]
                default_threshold = thresholds.get('DEFAULT', 0.70)
                
                for result in analyzer_results:
                    entity_type = result.entity_type
                    threshold = thresholds.get(entity_type, default_threshold)
                    
                    if result.score >= threshold:
                        entity_dict = {
                            'start': result.start,
                            'end': result.end,
                            'score': result.score,
                            'entity_type': result.entity_type,
                            'analysis_explanation': result.analysis_explanation,
                            'text': text[result.start:result.end]
                        }
                        other_results.append(entity_dict)
                
                # Combinar resultados y devolverlos
                return person_entities + other_results
            else:
                # Análisis estándar con Presidio
                analyzer_results = self.analyzer.analyze(
                    text=text, 
                    language=language,
                    entities=entities
                )
                
                # Convertir resultados a diccionario y filtrar por umbral
                if language not in ENTITY_THRESHOLDS:
                    language = DEFAULT_LANGUAGE
                
                thresholds = ENTITY_THRESHOLDS[language]
                default_threshold = thresholds.get('DEFAULT', 0.70)
                
                filtered_results = []
                for result in analyzer_results:
                    entity_type = result.entity_type
                    threshold = thresholds.get(entity_type, default_threshold)
                    
                    if result.score >= threshold:
                        entity_dict = {
                            'start': result.start,
                            'end': result.end,
                            'score': result.score,
                            'entity_type': result.entity_type,
                            'analysis_explanation': result.analysis_explanation,
                            'text': text[result.start:result.end]
                        }
                        filtered_results.append(entity_dict)
                
                return filtered_results

        except Exception as e:
            self.logger.error(f"Error durante el análisis: {str(e)}")
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
            # Crear un ResultRecognizer
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

            self.logger.info(
                f"Texto anonimizado correctamente. Entidades reemplazadas: {len(results)}"
            )
            return {
                "text": anonymize_result.text,
                "items": [dict(item) for item in anonymize_result.items],
            }
        except Exception as e:
            self.logger.error(f"Error durante la anonimización: {str(e)}")
            return {"text": text, "items": [], "error": str(e)}
