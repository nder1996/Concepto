from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PresidioService:
    def __init__(self):
        # Configuramos correctamente el motor NLP con soporte para español
        try:
            # Crear el motor NLP con modelos tanto en inglés como en español
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "en", "model_name": "en_core_web_lg"},
                    {"lang_code": "es", "model_name": "es_core_news_md"}
                ]
            }
            
            nlp_engine_provider = NlpEngineProvider(nlp_configuration=nlp_config)
            nlp_engine = nlp_engine_provider.create_engine()
            
            # Inicializar el analizador con el motor NLP configurado
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self.anonymizer = AnonymizerEngine()
            
            logger.info("PresidioService inicializado con soporte para inglés y español")
        except Exception as e:
            logger.error(f"Error al inicializar PresidioService: {str(e)}")
            # Fallback al motor predeterminado si hay errores
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            logger.warning("Usando motor de análisis predeterminado debido a errores")
        
        # Diccionario con entidades y sus umbrales de confianza predeterminados
        self.entities_thresholds = {
            "PERSON": 0.6,           # Nombres de personas
            "PHONE_NUMBER": 0.7,     # Teléfonos
            "LOCATION": 0.6,         # Ubicaciones
            "DATE_TIME": 0.6,        # Referencias de tiempo
            "NRP": 0.8,              # Cédula/documento de identidad
            "EMAIL_ADDRESS": 0.8,    # Correos electrónicos
            "ADDRESS": 0.65          # Direcciones
        }
      def analyze_text(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades encontradas"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            results = self.analyzer.analyze(text=text, language=language)
            return [{
                'entity_type': r.entity_type,
                'start': r.start,
                'end': r.end,
                'score': r.score
            } for r in results]
        except Exception as e:
            logger.error(f"Error al analizar texto: {str(e)}")
            return []
    
    def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            results = self.analyzer.analyze(text=text, language=language)
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized.text
        except Exception as e:
            logger.error(f"Error al anonimizar texto: {str(e)}")
            return textdef anonymize_specific_entities(self, text: str, language: str = 'en', 
                                   custom_thresholds: Dict[str, float] = None) -> str:
        """
        Anonimiza solo entidades específicas con umbrales de confianza predeterminados para cada tipo:
        - PERSON (nombres de personas): 0.6
        - PHONE_NUMBER (números telefónicos): 0.7
        - LOCATION (ubicaciones): 0.6
        - DATE_TIME (referencias de tiempo): 0.6
        - NRP (cédula/documento de identidad): 0.8
        - EMAIL_ADDRESS (correos electrónicos): 0.8
        - ADDRESS (direcciones): 0.65
        
        Args:
            text: Texto a anonimizar
            language: Idioma del texto (por defecto 'en')
            custom_thresholds: Diccionario opcional para sobrescribir los umbrales predeterminados
            
        Returns:
            Texto anonimizado
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Crear un nuevo analizador especialmente para este análisis
        # Esto soluciona problemas de compatibilidad de idiomas
        try:
            # Usar un nuevo analizador con opciones explícitas para idioma
            import spacy
            from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
            from presidio_analyzer.predefined_recognizers import SpacyRecognizer
            
            # Verificar que el modelo de lenguaje esté disponible
            try:
                if language == 'es':
                    if not spacy.util.is_package("es_core_news_md"):
                        # Fallback al modelo pequeño si el mediano no está disponible
                        if spacy.util.is_package("es_core_news_sm"):
                            logger.warning("Usando modelo español pequeño en lugar del mediano")
                            spacy_model = "es_core_news_sm"
                        else:
                            logger.warning("No se encontró modelo para español, usando inglés")
                            language = 'en'
                            spacy_model = "en_core_web_lg"
                    else:
                        spacy_model = "es_core_news_md"
                else:
                    # Para inglés u otros idiomas
                    if not spacy.util.is_package("en_core_web_lg"):
                        if spacy.util.is_package("en_core_web_sm"):
                            logger.warning("Usando modelo inglés pequeño en lugar del grande")
                            spacy_model = "en_core_web_sm"
                        else:
                            logger.error("No se encontraron modelos de spaCy")
                            return text
                    else:
                        spacy_model = "en_core_web_lg"
                
                # Cargar el modelo de spaCy adecuado
                nlp = spacy.load(spacy_model)
                
                # Configurar un nuevo analizador con el modelo cargado
                registry = RecognizerRegistry()
                registry.load_predefined_recognizers()
                
                # Registrar reconocedores personalizados para aumentar reconocimiento
                recognizer_es = SpacyRecognizer(supported_language=language, supported_entities=None)
                registry.add_recognizer(recognizer_es)
                
                # Crear un nuevo analizador con el registro personalizado
                custom_analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp)
                
                # Usar umbrales personalizados si se proporcionan
                thresholds = self.entities_thresholds.copy()
                if custom_thresholds:
                    thresholds.update(custom_thresholds)
                
                # Analizar texto con el analizador personalizado
                all_results = custom_analyzer.analyze(text=text, language=language)
                
                # Ejecutar análisis de diagnóstico
                logger.info(f"Análisis de texto ({language}): encontradas {len(all_results)} entidades")
                for result in all_results:
                    logger.info(f"Entidad: {result.entity_type}, Score: {result.score}, Texto: {text[result.start:result.end]}")
                
                # Filtrar entidades por tipo y umbral
                filtered_results = [r for r in all_results 
                                   if r.entity_type in thresholds and 
                                   r.score >= thresholds[r.entity_type]]
                
                logger.info(f"Después del filtrado: {len(filtered_results)} entidades")
                
                # Anonimizar solo las entidades filtradas
                if filtered_results:
                    anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
                    return anonymized.text
                else:
                    logger.warning("No hay entidades que cumplan con los umbrales de confianza requeridos")
                    return text
                
            except Exception as e:
                logger.error(f"Error cargando modelo de lenguaje: {str(e)}")
                # Intentar con el analizador predeterminado
                return self._fallback_anonymize(text, language, custom_thresholds)
                
        except Exception as e:
            logger.error(f"Error en anonymize_specific_entities: {str(e)}")
            return text
            
    def _fallback_anonymize(self, text: str, language: str, custom_thresholds: Dict[str, float] = None) -> str:
        """Método de respaldo cuando falla la anonimización personalizada"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Usar el analizador predeterminado
            all_results = self.analyzer.analyze(text=text, language=language)
            
            # Obtener umbrales
            thresholds = self.entities_thresholds.copy()
            if custom_thresholds:
                thresholds.update(custom_thresholds)
            
            # Filtrar resultados
            filtered_results = [r for r in all_results 
                              if r.entity_type in thresholds and 
                              r.score >= thresholds[r.entity_type]]
            
            if filtered_results:
                anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
                return anonymized.text
            else:
                return text
                
        except Exception as e:
            logger.error(f"Error en fallback: {str(e)}")
            return text