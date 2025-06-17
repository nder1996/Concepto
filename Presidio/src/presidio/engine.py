"""
Módulo central para la integración con Microsoft Presidio.

Este módulo proporciona una capa de abstracción sobre los motores de análisis y anonimización
de Presidio, ofreciendo funcionalidades adaptadas a necesidades específicas, especialmente
para el contexto colombiano y latinoamericano.

Incluye:
- Carga y gestión de reconocedores personalizados
- Configuración de motores de NLP para español e inglés
- Integración de validadores contextuales avanzados
- Soporte para múltiples idiomas (principalmente español e inglés)
- Umbrales configurables para diferentes tipos de entidades
"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
import spacy
from typing import List, Dict, Any, Optional, Tuple, Union
import os
import logging

# Importar reconocedores personalizados
from .recognizers.co_identity_recognizer import create_colombian_recognizers
from .recognizers.email_recognizer import EmailRecognizer
from .recognizers.phone_recognizer import PhoneRecognizer

# Intentar importar el validador Flair (opcional)
try:
    from .recognizers.validators.flair_validator import FlairValidator
    FLAIR_DISPONIBLE = True
except ImportError:
    FLAIR_DISPONIBLE = False

# Configurar logger
logger = logging.getLogger("presidio.engine")

class PresidioEngine:
    """
    Motor central de integración con Presidio.
    
    Esta clase proporciona una interfaz unificada para los servicios de análisis y anonimización
    de Presidio, con soporte para múltiples idiomas y reconocedores personalizados.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el motor de Presidio con configuraciones personalizadas.
        
        Args:
            config: Configuración opcional con parámetros como:
                - idioma_predeterminado: Idioma por defecto ('es' o 'en')
                - umbral_confianza: Diccionario de umbrales por tipo de entidad
                - modo_validacion: Nivel de validación (básico, medio, estricto)
        """
        self.logger = logger
        self.logger.info("Inicializando motor de Presidio...")
        
        # Configuraciones predeterminadas
        self.config = {
            "idioma_predeterminado": "es",
            "idiomas_soportados": ["es", "en"],
            "umbral_confianza": {
                "global": 0.65,
                "PERSON": 0.6,
                "PHONE_NUMBER": 0.5,
                "EMAIL_ADDRESS": 0.6,
                "CO_ID_NUMBER": 0.7
            },
            "modo_validacion": "medio",  # básico, medio, estricto
            "anonimizar_contexto": False  # Si True, anonimiza más contexto alrededor de la entidad
        }
        
        # Actualizar con configuraciones personalizadas si se proporcionan
        if config:
            self.config.update(config)
            
        # Verificar modo de ejecución (Docker o local)
        self.en_docker = os.environ.get('RUNNING_IN_DOCKER', 'False').lower() == 'true'
        if self.en_docker:
            self.logger.info("Ejecutando en entorno Docker")
        else:
            self.logger.info("Ejecutando en entorno local")
        
        # Inicializar motores NLP, analizadores y anonimizador
        self._init_nlp_engines()
        self._init_analyzers()
        self._init_anonymizer()
        
        self.logger.info("Motor de Presidio inicializado correctamente")
        
    def _init_nlp_engines(self):
        """Inicializa los motores NLP para diferentes idiomas."""
        self.logger.info("Inicializando motores NLP...")
        self.nlp_engines = {}
        
        try:
            # Cargar modelo para español
            self.logger.info("Cargando modelo spaCy para español...")
            nlp_config_es = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "es", "model_name": "es_core_news_sm"}],
            }
            nlp_provider_es = NlpEngineProvider(nlp_configuration=nlp_config_es)
            self.nlp_engines["es"] = nlp_provider_es.create_engine()
            
            # Cargar modelo para inglés
            self.logger.info("Cargando modelo spaCy para inglés...")
            nlp_config_en = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            nlp_provider_en = NlpEngineProvider(nlp_configuration=nlp_config_en)
            self.nlp_engines["en"] = nlp_provider_en.create_engine()
            
            self.logger.info("Motores NLP inicializados correctamente")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar motores NLP: {str(e)}")
            raise
            
    def _init_analyzers(self):
        """Inicializa los analizadores con reconocedores personalizados por idioma."""
        self.logger.info("Inicializando analizadores con reconocedores personalizados...")
        self.analyzers = {}
        
        try:
            # Configurar analizador para español
            registry_es = RecognizerRegistry()
            registry_es.load_predefined_recognizers(nlp_engine=self.nlp_engines["es"])
            
            # Añadir reconocedores colombianos (solo para español)
            self.logger.info("Registrando reconocedores de documentos colombianos...")
            for recognizer in create_colombian_recognizers():
                registry_es.add_recognizer(recognizer)
                
            # Añadir reconocedor de correos electrónicos para español
            self.logger.info("Registrando reconocedor de correos electrónicos para español...")
            email_recognizer_es = EmailRecognizer(supported_language="es")
            registry_es.add_recognizer(email_recognizer_es)
            
            # Añadir reconocedor de números telefónicos para español
            self.logger.info("Registrando reconocedor de teléfonos para español...")
            phone_recognizer_es = PhoneRecognizer(supported_language="es")
            registry_es.add_recognizer(phone_recognizer_es)
            
            # Crear analizador para español
            self.analyzers["es"] = AnalyzerEngine(
                registry=registry_es, 
                nlp_engine=self.nlp_engines["es"]
            )
            
            # Configurar analizador para inglés
            registry_en = RecognizerRegistry()
            registry_en.load_predefined_recognizers(nlp_engine=self.nlp_engines["en"])
            
            # Añadir reconocedor de correos electrónicos para inglés
            self.logger.info("Registrando reconocedor de correos electrónicos para inglés...")
            email_recognizer_en = EmailRecognizer(supported_language="en")
            registry_en.add_recognizer(email_recognizer_en)
            
            # Añadir reconocedor de números telefónicos para inglés
            self.logger.info("Registrando reconocedor de teléfonos para inglés...")
            phone_recognizer_en = PhoneRecognizer(supported_language="en")
            registry_en.add_recognizer(phone_recognizer_en)
            
            # Crear analizador para inglés
            self.analyzers["en"] = AnalyzerEngine(
                registry=registry_en, 
                nlp_engine=self.nlp_engines["en"]
            )
            
            self.logger.info("Analizadores inicializados correctamente")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar analizadores: {str(e)}")
            raise
    
    def _init_anonymizer(self):
        """Inicializa el motor de anonimización."""
        self.logger.info("Inicializando motor de anonimización...")
        
        try:
            self.anonymizer = AnonymizerEngine()
            self.logger.info("Motor de anonimización inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar motor de anonimización: {str(e)}")
            raise
    
    def _get_entity_threshold(self, entity_type: str, language: str) -> float:
        """
        Obtiene el umbral de confianza para un tipo específico de entidad y lenguaje.
        
        Args:
            entity_type: Tipo de entidad (ej: "PERSON", "PHONE_NUMBER")
            language: Código de idioma (ej: "es", "en")
            
        Returns:
            float: Umbral de confianza
        """
        # Primero intentar con combinación de entidad y lenguaje
        threshold_key = f"{entity_type}_{language}"
        if threshold_key in self.config["umbral_confianza"]:
            return self.config["umbral_confianza"][threshold_key]
        
        # Luego intentar solo con la entidad
        if entity_type in self.config["umbral_confianza"]:
            return self.config["umbral_confianza"][entity_type]
        
        # Finalmente, usar umbral global
        return self.config["umbral_confianza"]["global"]
    
    def analyze(self, 
                text: str, 
                language: Optional[str] = None,
                entities: Optional[List[str]] = None,
                return_decision_process: bool = False) -> List[Dict[str, Any]]:
        """
        Analiza un texto para detectar información sensible.
        
        Args:
            text: Texto a analizar
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            entities: Lista de tipos de entidades a buscar. Si es None, se buscan todas.
            return_decision_process: Si es True, incluye información sobre el proceso de decisión
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades detectadas con detalles
        """
        # Validar idioma
        language = language or self.config["idioma_predeterminado"]
        if language not in self.config["idiomas_soportados"]:
            self.logger.warning(f"Idioma no soportado: {language}. Usando idioma predeterminado.")
            language = self.config["idioma_predeterminado"]
        
        # Validar y preparar entidades a buscar
        if entities is None:
            # Lista completa de entidades a buscar
            entities = [
                "PERSON",
                "PHONE_NUMBER",
                "EMAIL_ADDRESS",
                "CO_ID_NUMBER",  # Genérico para documentos colombianos
                "CO_ID_NUMBER_CC",  # Específico para cédula
                "CO_ID_NUMBER_TI",  # Específico para tarjeta de identidad
                "CO_ID_NUMBER_CE",  # Específico para cédula de extranjería
                "CO_ID_NUMBER_RC",  # Específico para registro civil
                "CO_ID_NUMBER_PA",  # Específico para pasaporte
                "CO_ID_NUMBER_NIT",  # Específico para NIT
                "CO_ID_NUMBER_PEP",  # Específico para PEP
            ]
            
            # Si es idioma inglés, quitar los tipos de documentos colombianos
            if language == "en":
                entities = [e for e in entities if not e.startswith("CO_ID_NUMBER")]
        
        # Obtener analizador para el idioma especificado
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(f"No se encontró analizador para el idioma: {language}")
            return []
            
        # Analizar el texto
        self.logger.info(f"Analizando texto en {language} ({len(text)} caracteres)")
        results = analyzer.analyze(text=text, language=language, entities=entities)
        
        # Filtrar resultados según umbrales configurados
        filtered_results = []
        for result in results:
            threshold = self._get_entity_threshold(result.entity_type, language)
            
            if result.score >= threshold:
                # Construir diccionario de resultado
                result_dict = {
                    "entity_type": result.entity_type,
                    "start": result.start,
                    "end": result.end,
                    "score": float(result.score),  # Convertir a float nativo para serialización JSON
                    "text": text[result.start:result.end],
                    "language": language
                }
                
                # Incluir información adicional sobre el proceso de decisión si se solicita
                if return_decision_process and hasattr(result, "analysis_explanation"):
                    result_dict["decision_process"] = result.analysis_explanation
                
                filtered_results.append(result_dict)
        
        self.logger.info(f"Análisis completado. Entidades detectadas: {len(filtered_results)}")
        return filtered_results
    
    def anonymize(self, 
                  text: str, 
                  language: Optional[str] = None,
                  entities: Optional[List[str]] = None,
                  operators: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Anonimiza un texto reemplazando información sensible.
        
        Args:
            text: Texto a anonimizar
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            entities: Lista de tipos de entidades a anonimizar. Si es None, se anonimizarán todas.
            operators: Diccionario de operadores de anonimización por tipo de entidad
            
        Returns:
            Dict[str, Any]: Diccionario con el texto anonimizado y estadísticas
        """
        # Primero analizar para obtener las entidades
        analyzed_results = self.analyze(
            text=text, 
            language=language, 
            entities=entities
        )
        
        # Si no hay resultados, devolver el texto original
        if not analyzed_results:
            return {
                "text": text,
                "original_length": len(text),
                "anonymized_length": len(text),
                "anonymized_entities": 0,
                "language": language or self.config["idioma_predeterminado"]
            }
        
        # Convertir resultados analizados al formato esperado por el anonimizador
        analyzer_results_for_anonymizer = []
        for result in analyzed_results:
            from presidio_analyzer import RecognizerResult
            analyzer_result = RecognizerResult(
                entity_type=result["entity_type"],
                start=result["start"],
                end=result["end"],
                score=result["score"]
            )
            analyzer_results_for_anonymizer.append(analyzer_result)
        
        # Configurar operadores de anonimización si se proporcionan
        anonymizer_config = {}
        if operators:
            anonymizer_config["operators"] = operators
        
        # Realizar la anonimización
        self.logger.info(f"Anonimizando texto con {len(analyzer_results_for_anonymizer)} entidades")
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results_for_anonymizer,
            **anonymizer_config
        )
        
        # Preparar respuesta con estadísticas
        response = {
            "text": anonymized_result.text,
            "original_length": len(text),
            "anonymized_length": len(anonymized_result.text),
            "anonymized_entities": len(analyzer_results_for_anonymizer),
            "language": language or self.config["idioma_predeterminado"],
            "items": []  # Lista de elementos anonimizados con detalles
        }
        
        # Añadir detalles de cada elemento anonimizado
        for item in anonymized_result.items:
            response["items"].append({
                "entity_type": item.entity_type,
                "start": item.start,
                "end": item.end,
                "text": item.text,
                "operator": item.operator
            })
        
        self.logger.info(f"Anonimización completada. Texto resultante: {len(response['text'])} caracteres")
        return response
    
    def get_supported_entities(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de entidades soportadas por el motor.
        
        Args:
            language: Código de idioma (ej: "es", "en"). Si es None, se usan todas.
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades con detalles
        """
        # Si se especifica un idioma, obtener solo las entidades para ese idioma
        if language and language in self.analyzers:
            analyzer = self.analyzers[language]
            recognizers = analyzer.registry.recognizers
        else:
            # Combinar reconocedores de todos los idiomas soportados
            recognizers = []
            for lang, analyzer in self.analyzers.items():
                recognizers.extend(analyzer.registry.recognizers)
        
        # Eliminar duplicados por nombre
        unique_recognizers = {}
        for recognizer in recognizers:
            if recognizer.name not in unique_recognizers:
                unique_recognizers[recognizer.name] = recognizer
        
        # Construir lista de entidades
        entities = []
        for name, recognizer in unique_recognizers.items():
            entity_info = {
                "name": name,
                "supported_entity": recognizer.supported_entity,
                "supported_language": recognizer.supported_language,
            }
            
            # Añadir patrones si están disponibles
            if hasattr(recognizer, "patterns") and recognizer.patterns:
                entity_info["patterns"] = [
                    {"name": pattern.name, "score": pattern.score}
                    for pattern in recognizer.patterns
                ]
            
            entities.append(entity_info)
        
        return entities
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado de salud del motor.
        
        Returns:
            Dict[str, Any]: Estado de salud con detalles
        """
        status = {
            "status": "healthy",
            "version": "1.0.0",  # Versión del motor
            "languages": self.config["idiomas_soportados"],
            "default_language": self.config["idioma_predeterminado"],
            "running_in_docker": self.en_docker,
            "flair_available": FLAIR_DISPONIBLE,
            "entities": {}
        }
        
        # Añadir información sobre los reconocedores por idioma
        for language, analyzer in self.analyzers.items():
            status["entities"][language] = []
            for recognizer in analyzer.registry.recognizers:
                status["entities"][language].append({
                    "name": recognizer.name,
                    "entity": recognizer.supported_entity,
                })
        
        return status