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
          # Verificar que los reconocedores personalizados estén registrados
        self._verify_custom_recognizers()
    
    def _verify_custom_recognizers(self):
        """
        Verifica que los reconocedores personalizados estén correctamente registrados.
        """
        for lang, analyzer in self.analyzers.items():
            registry = analyzer.registry
            recognizer_names = [r.name for r in registry.recognizers]
            
            # Agregar detalles de cada reconocedor para mejor depuración
            self.logger.info(f"Verificando reconocedores para idioma {lang}:")
            for r in registry.recognizers:
                recognizer_details = {
                    'name': getattr(r, 'name', 'sin nombre'),
                    'supported_entity': getattr(r, 'supported_entity', 'N/A'),
                    'supported_language': getattr(r, 'supported_language', 'N/A'),
                }
                self.logger.debug(f"Reconocedor: {recognizer_details}")
            
            # Verificar específicamente que el reconocedor COLOMBIAN_LOCATION esté disponible
            location_recognizers = []
            for r in registry.recognizers:
                try:
                    # Verificar si el reconocedor tiene el atributo supported_entity
                    if hasattr(r, 'supported_entity') and r.supported_entity == "COLOMBIAN_LOCATION":
                        location_recognizers.append(r)
                        self.logger.debug(f"Encontrado reconocedor COLOMBIAN_LOCATION: {r.name} para idioma {getattr(r, 'supported_language', 'N/A')}")
                    # También verificar si el reconocedor tiene el atributo entity_name
                    elif hasattr(r, 'entity_name') and r.entity_name == "COLOMBIAN_LOCATION":
                        location_recognizers.append(r)
                    # Verificar otros posibles atributos
                    elif hasattr(r, 'entities') and "COLOMBIAN_LOCATION" in r.entities:
                        location_recognizers.append(r)
                except Exception as e:
                    self.logger.warning(f"Error al verificar reconocedor {r.name if hasattr(r, 'name') else 'desconocido'}: {str(e)}")
            
            if location_recognizers:
                self.logger.info(f"Reconocedor COLOMBIAN_LOCATION disponible en idioma {lang}")
            else:
                self.logger.warning(f"¡IMPORTANTE! Reconocedor COLOMBIAN_LOCATION NO disponible en idioma {lang}")
                
            # Mostrar todos los reconocedores disponibles para este idioma
           # self.logger.info(f"Reconocedores disponibles para {lang}: {', '.join(recognizer_names)}")
            
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
            )
            
        # Detectar posibles superposiciones entre COLOMBIAN_ID_DOC y PHONE_NUMBER
        overlapping_entities = {}
        for i, r1 in enumerate(results):
            for j, r2 in enumerate(results):
                if i != j and r1.entity_type != r2.entity_type:
                    # Verificar si hay superposición
                    if (r1.start <= r2.end and r2.start <= r1.end):
                        # Si una es COLOMBIAN_ID_DOC y otra es PHONE_NUMBER, guardamos el índice del PHONE_NUMBER
                        if r1.entity_type == "COLOMBIAN_ID_DOC" and r2.entity_type == "PHONE_NUMBER":
                            overlapping_entities[j] = "PHONE_NUMBER"
                        elif r1.entity_type == "PHONE_NUMBER" and r2.entity_type == "COLOMBIAN_ID_DOC":
                            overlapping_entities[i] = "PHONE_NUMBER"
        
        # Filtrar resultados eliminando los PHONE_NUMBER que se solapan con COLOMBIAN_ID_DOC
        filtered_results = []
        for i, r in enumerate(results):
            # Si es un teléfono que se solapa con una cédula, lo ignoramos
            if i in overlapping_entities and overlapping_entities[i] == "PHONE_NUMBER":
                self.logger.info(f"Ignorando número telefónico que se solapa con cédula: {text[r.start:r.end]}")
                continue
                
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
            'start': r.start,
            'end': r.end,
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
            
        # Detectar posibles superposiciones entre COLOMBIAN_ID_DOC y PHONE_NUMBER
        overlapping_entities = {}
        for i, r1 in enumerate(results):
            for j, r2 in enumerate(results):
                if i != j and r1.entity_type != r2.entity_type:
                    # Verificar si hay superposición
                    if (r1.start <= r2.end and r2.start <= r1.end):
                        # Si una es COLOMBIAN_ID_DOC y otra es PHONE_NUMBER, guardamos el índice del PHONE_NUMBER
                        if r1.entity_type == "COLOMBIAN_ID_DOC" and r2.entity_type == "PHONE_NUMBER":
                            overlapping_entities[j] = "PHONE_NUMBER"
                        elif r1.entity_type == "PHONE_NUMBER" and r2.entity_type == "COLOMBIAN_ID_DOC":
                            overlapping_entities[i] = "PHONE_NUMBER"
        
        # Filtrar resultados eliminando los PHONE_NUMBER que se solapan con COLOMBIAN_ID_DOC
        filtered_results = []
        for i, r in enumerate(results):
            # Si es un teléfono que se solapa con una cédula, lo ignoramos
            if i in overlapping_entities and overlapping_entities[i] == "PHONE_NUMBER":
                self.logger.info(f"Ignorando número telefónico que se solapa con cédula: {text[r.start:r.end]}")
                continue
                
            # Aplicar filtro de umbral y entidades objetivo
            if r.entity_type in self.target_entities and r.score >= thresholds.get(r.entity_type, 0.80):
                filtered_results.append(r)
        
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