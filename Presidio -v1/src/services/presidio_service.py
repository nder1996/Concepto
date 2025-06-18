from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import spacy
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.utils.logger import setup_logger
from src.config.entity_config import TARGET_ENTITIES, ENTITY_THRESHOLDS, THRESHOLDS_BY_LANGUAGE
from src.utils.custom_recognizers import register_custom_recognizers

class PresidioService:
    def __init__(self):
        self.logger = setup_logger("PresidioService")
        
        # Inicializar analizadores para diferentes idiomas
        self.logger.info("Inicializando analizadores para diferentes idiomas...")
        
        try:
            # Configurar motores NLP para cada idioma soportado usando los modelos específicos
            self.nlp_engines = {}
            
            # Configurar NLP Engine para español con modelo específico
            try:
                # Intentar cargar el modelo en español
                self.logger.info("Cargando modelo para español (es_core_news_md)...")
                configuration_es = {
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "es", "model_name": "es_core_news_md"}]
                }
                provider_es = NlpEngineProvider(nlp_configuration=configuration_es)
                nlp_engine_es = provider_es.create_engine()
                
                # Crear registro de reconocedores para español
                registry_es = RecognizerRegistry()
                register_custom_recognizers(registry_es)
                
                # Crear analizador con el motor NLP específico para español
                self.analyzer_es = AnalyzerEngine(
                    registry=registry_es,
                    nlp_engine=nlp_engine_es
                )
                self.logger.info("Motor NLP para español inicializado correctamente.")
            except Exception as e:
                self.logger.error(f"Error al cargar el modelo español: {str(e)}")
                self.logger.warning("Usando configuración de respaldo para español...")
                # Si falla, usamos un registro normal sin modelo específico
                registry_es = RecognizerRegistry()
                register_custom_recognizers(registry_es)
                self.analyzer_es = AnalyzerEngine(registry=registry_es)
            
            # Configurar NLP Engine para inglés con modelo específico
            try:
                # Intentar cargar el modelo en inglés
                self.logger.info("Cargando modelo para inglés (en_core_web_lg)...")
                configuration_en = {
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]
                }
                provider_en = NlpEngineProvider(nlp_configuration=configuration_en)
                nlp_engine_en = provider_en.create_engine()
                
                # Crear registro de reconocedores para inglés
                registry_en = RecognizerRegistry()
                register_custom_recognizers(registry_en)
                
                # Crear analizador con el motor NLP específico para inglés
                self.analyzer_en = AnalyzerEngine(
                    registry=registry_en,
                    nlp_engine=nlp_engine_en
                )
                self.logger.info("Motor NLP para inglés inicializado correctamente.")
            except Exception as e:
                self.logger.error(f"Error al cargar el modelo inglés: {str(e)}")
                self.logger.warning("Usando configuración de respaldo para inglés...")
                # Si falla, usamos un registro normal sin modelo específico
                registry_en = RecognizerRegistry()
                register_custom_recognizers(registry_en)
                self.analyzer_en = AnalyzerEngine(registry=registry_en)
            
            # Diccionario de analizadores por idioma
            self.analyzers = {"es": self.analyzer_es, "en": self.analyzer_en}
            self.logger.info("Motores de análisis inicializados correctamente para todos los idiomas.")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar los motores de análisis: {str(e)}")
            raise
            
        # Inicializar el motor de anonimización
        self.anonymizer = AnonymizerEngine()
          # Idiomas soportados
        self.supported_languages = ["en", "es"]
        self.default_language = "es"  # Español como idioma predeterminado
        # Usar configuración centralizada
        self.target_entities = TARGET_ENTITIES
        self.thresholds_by_language = THRESHOLDS_BY_LANGUAGE
        # Registrar la inicialización
        self.logger.info(f"Servicio Presidio inicializado con soporte para idiomas: {', '.join(self.supported_languages)}")
        
    def analyze_text(self, text: str, language: str = 'es') -> List[Dict[str, Any]]:
        """Analiza texto y retorna solo las entidades específicas que superen el umbral configurado"""
        # Validar idioma y usar el predeterminado si no es soportado
        if language not in self.supported_languages:
            self.logger.warning(f"Idioma '{language}' no soportado, usando idioma predeterminado: {self.default_language}")
            language = self.default_language
            
        # Seleccionar el analizador correspondiente al idioma
        analyzer = self.analyzers.get(language, self.analyzer_en)
        self.logger.info(f"Utilizando analizador para idioma: {language}")
        
        # Obtener umbrales específicos para el idioma
        thresholds = self.thresholds_by_language.get(language, self.thresholds_by_language['en'])
        self.logger.info(f"Utilizando umbrales para idioma: {language}")
        
        # Analizar el texto completo
        results = analyzer.analyze(text=text, language=language)
        
        # Registrar todas las entidades detectadas originalmente
        self.logger.info(f"Total de entidades detectadas: {len(results)}")
        for r in results:
            self.logger.info(
                f"Entidad detectada: {r.entity_type}, "
                f"Score: {r.score}, Texto: {text[r.start:r.end]}"
            )
        
        # Filtrar solo las entidades objetivo que superan el umbral específico para el idioma
        filtered_results = [r for r in results 
                            if r.entity_type in self.target_entities
                            and r.score >= thresholds.get(r.entity_type, 0.80)]
        
        # Registrar las entidades que superan el filtro
        self.logger.info(f"Entidades que superan el umbral: {len(filtered_results)}")
        for r in filtered_results:
            threshold = thresholds.get(r.entity_type, 0.80)
            self.logger.info(
                f"Entidad considerada: {r.entity_type}, "
                f"Score: {r.score} (umbral: {threshold}), Texto: {text[r.start:r.end]}"
            )
        return [{
            'entity_type': r.entity_type,
            'start': r.start,            'end': r.end,
            'score': r.score
        } for r in filtered_results]
        
    def anonymize_text(self, text: str, language: str = 'es') -> str:
        """Anonimiza texto reemplazando solo entidades específicas con puntaje superior al umbral"""
        # Validar idioma y usar el predeterminado si no es soportado
        if language not in self.supported_languages:
            self.logger.warning(f"Idioma '{language}' no soportado, usando idioma predeterminado: {self.default_language}")
            language = self.default_language
            
        # Seleccionar el analizador correspondiente al idioma
        analyzer = self.analyzers.get(language, self.analyzer_en)
        self.logger.info(f"Utilizando analizador para idioma: {language}")
        
        # Obtener umbrales específicos para el idioma
        thresholds = self.thresholds_by_language.get(language, self.thresholds_by_language['en'])
        self.logger.info(f"Utilizando umbrales para idioma: {language}")
        
        # Analizar el texto completo
        results = analyzer.analyze(text=text, language=language)
        
        # Registrar todas las entidades detectadas originalmente
        self.logger.info(f"Total de entidades detectadas: {len(results)}")
        for r in results:
            self.logger.info(
                f"Entidad detectada: {r.entity_type}, "
                f"Score: {r.score}, Texto: {text[r.start:r.end]}"
            )
        
        # Filtrar solo las entidades objetivo con puntaje mayor al umbral específico para el idioma
        filtered_results = [r for r in results
                        if r.entity_type in self.target_entities
                        and r.score >= thresholds.get(r.entity_type, 0.80)]
        
        # Registrar las entidades que SÍ serán anonimizadas
        self.logger.info(f"Entidades que serán anonimizadas: {len(filtered_results)}")
        for r in filtered_results:
            threshold = thresholds.get(r.entity_type, 0.80)
            self.logger.info(
                f"Entidad anonimizada: {r.entity_type}, "
                f"Score: {r.score} (umbral: {threshold}), Texto: {text[r.start:r.end]}"
            )
        
        # Anonimizar solo las entidades filtradas
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text