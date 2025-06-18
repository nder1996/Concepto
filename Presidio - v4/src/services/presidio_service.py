from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import spacy
from src.utils.logger import setup_logger
from src.config.entity_config import TARGET_ENTITIES, ENTITY_THRESHOLDS, THRESHOLDS_BY_LANGUAGE
from src.config.language_config import initialize_language_analyzers, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

class PresidioService:
    def __init__(self):
        self.logger = setup_logger("PresidioService")
        
        # Inicializar analizadores para diferentes idiomas desde language_config
        self.logger.info("Inicializando analizadores para diferentes idiomas...")
        try:
            # Obtener los analizadores configurados para cada idioma
            self.analyzers = initialize_language_analyzers()
            self.logger.info("Motores de análisis inicializados correctamente.")
        except Exception as e:
            self.logger.error(f"Error al inicializar los motores de análisis: {str(e)}")
            raise
            
        # Inicializar el motor de anonimización
        self.anonymizer = AnonymizerEngine()
          # Idiomas soportados (importados de language_config)
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
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
        if language in self.analyzers:
            analyzer = self.analyzers[language]
        else:
            # Si no tenemos un analizador para el idioma, usamos el analizador del idioma predeterminado
            self.logger.warning(f"No se encontró analizador para el idioma {language}, usando el analizador predeterminado")
            analyzer = self.analyzers[self.default_language]
            
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
            )          # Filtrar solo las entidades objetivo que superan el umbral específico para el idioma
        filtered_results = []
        for r in results:
            # Determinar el umbral apropiado para la entidad
            threshold = thresholds.get(r.entity_type, 0.80)
            
            # Incluir la entidad si está en target_entities y supera el umbral
            if r.entity_type in self.target_entities and r.score >= threshold:
                filtered_results.append(r)
        
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
        if language in self.analyzers:
            analyzer = self.analyzers[language]
        else:
            # Si no tenemos un analizador para el idioma, usamos el analizador del idioma predeterminado
            self.logger.warning(f"No se encontró analizador para el idioma {language}, usando el analizador predeterminado")
            analyzer = self.analyzers[self.default_language]
            
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