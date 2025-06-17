from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import spacy
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.utils.logger import setup_logger

# Importar reconocedores personalizados
from src.presidio.recognizers.email_recognizer import EmailRecognizer
from src.presidio.recognizers.phone_recognizer import PhoneRecognizer
from src.presidio.recognizers.co_identity_recognizer import ColombianIDRecognizer

# Intentar importar el validador Flair (opcional)
try:
    from src.presidio.recognizers.validators.flair_validator import FlairContextValidator
    FLAIR_DISPONIBLE = True
except ImportError:
    FLAIR_DISPONIBLE = False

class PresidioEngine:
    """
    Motor principal de integración con Presidio.
    Gestiona el análisis y anonimización de texto utilizando Presidio
    con reconocedores personalizados.
    """
    
    def __init__(self):
        # Inicializar logger
        self.logger = setup_logger("PresidioEngine")
        self.logger.info("Inicializando PresidioEngine...")
        
        # Idiomas soportados
        self.supported_languages = ["en", "es"]
        self.default_language = "es"
        
        # Configurar motores NLP para cada idioma soportado
        self.nlp_engines = {}
        self.analyzers = {}
        
        try:
            # Configurar para español
            self._setup_language_engine("es", "es_core_news_sm")
            
            # Configurar para inglés
            self._setup_language_engine("en", "en_core_web_sm")
            
            self.logger.info("Motores de análisis inicializados correctamente para todos los idiomas.")
        except Exception as e:
            self.logger.error(f"Error al inicializar los motores de análisis: {str(e)}")
            raise
        
        # Inicializar el motor de anonimización
        self.anonymizer = AnonymizerEngine()
        
        # Configurar las entidades objetivo
        self._setup_target_entities()
        
        # Configurar umbrales de entidades
        self._setup_entity_thresholds()
        
        self.logger.info("PresidioEngine inicializado con éxito")

    def _setup_language_engine(self, language_code, spacy_model):
        """Configura el motor NLP y el analizador para un idioma específico"""
        self.logger.info(f"Configurando motor para {language_code} usando modelo {spacy_model}...")
        
        # Cargar modelo de spaCy
        self.logger.info(f"Cargando modelo {spacy_model}...")
        _ = spacy.load(spacy_model)
        
        # Configurar NLP engine
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": language_code, "model_name": spacy_model}],
        }
        nlp_provider = NlpEngineProvider(nlp_configuration=nlp_config)
        nlp_engine = nlp_provider.create_engine()
        
        # Crear registro de reconocedores
        self.logger.info(f"Configurando reconocedores para {language_code}...")
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)
        
        # Registrar reconocedores personalizados
        self._register_custom_recognizers(registry, language_code)
        
        # Crear analizador
        analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
        
        # Guardar en diccionarios
        self.nlp_engines[language_code] = nlp_engine
        self.analyzers[language_code] = analyzer
        
        self.logger.info(f"Motor para {language_code} configurado con éxito")

    def _register_custom_recognizers(self, registry, language_code):
        """Registra los reconocedores personalizados para un idioma específico"""
        # Email recognizer
        self.logger.info(f"Registrando reconocedor de correos electrónicos para {language_code}...")
        email_recognizer = EmailRecognizer(supported_language=language_code)
        registry.add_recognizer(email_recognizer)
        
        # Phone recognizer
        self.logger.info(f"Registrando reconocedor de números telefónicos para {language_code}...")
        phone_recognizer = PhoneRecognizer(supported_language=language_code)
        registry.add_recognizer(phone_recognizer)
        
        # Solo para español: reconocedor de documentos de identidad colombianos
        if language_code == "es":
            self.logger.info("Registrando reconocedor de documentos de identidad colombianos...")
            id_recognizer = ColombianIDRecognizer(supported_language=language_code)
            registry.add_recognizer(id_recognizer)
            
            self.logger.info("Reconocedor de documentos colombianos configurado con los siguientes tipos:")
            self.logger.info("- Cédula de Ciudadanía (CC)")
            self.logger.info("- Tarjeta de Identidad (TI)")
            self.logger.info("- Cédula de Extranjería (CE)")
            self.logger.info("- Registro Civil (RC)")
            self.logger.info("- Pasaporte (PA)")
            self.logger.info("- NIT")
            self.logger.info("- Permiso Especial de Permanencia (PEP)")

    def _setup_target_entities(self):
        """Configura las entidades objetivo a detectar"""
        self.target_entities = [
            "PERSON",  # Nombres de personas
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            # Documentos de identidad colombianos y sus tipos específicos
            "CO_ID_NUMBER",  # Documento genérico
            "CO_ID_NUMBER_CC",  # Cédula de ciudadanía
            "CO_ID_NUMBER_TI",  # Tarjeta de identidad
            "CO_ID_NUMBER_CE",  # Cédula de extranjería
            "CO_ID_NUMBER_RC",  # Registro civil
            "CO_ID_NUMBER_PA",  # Pasaporte
            "CO_ID_NUMBER_NIT",  # NIT
            "CO_ID_NUMBER_PEP",  # Permiso Especial de Permanencia
        ]
        
        self.logger.info(f"Entidades objetivo configuradas: {len(self.target_entities)}")

    def _setup_entity_thresholds(self):
        """Configura los umbrales para cada tipo de entidad y por idioma"""
        # Umbrales para inglés
        self.entity_thresholds_en = {
            "PERSON": 0.1,  # Umbral bajo para capturar más candidatos
            "PHONE_NUMBER": 0.3,
            "EMAIL_ADDRESS": 0.6,
            "CO_ID_NUMBER": 0.65,
            "CO_ID_NUMBER_CC": 0.60,
            "CO_ID_NUMBER_TI": 0.65,
            "CO_ID_NUMBER_CE": 0.65,
            "CO_ID_NUMBER_RC": 0.65,
            "CO_ID_NUMBER_PA": 0.70,
            "CO_ID_NUMBER_NIT": 0.70,
            "CO_ID_NUMBER_PEP": 0.70,
        }
        
        # Umbrales para español - ajustados para mejor detección
        self.entity_thresholds_es = {
            "PERSON": 0.1,
            "PHONE_NUMBER": 0.3,
            "EMAIL_ADDRESS": 0.6,
            "CO_ID_NUMBER": 0.5,
            "CO_ID_NUMBER_CC": 0.45,
            "CO_ID_NUMBER_TI": 0.5,
            "CO_ID_NUMBER_CE": 0.5,
            "CO_ID_NUMBER_RC": 0.5,
            "CO_ID_NUMBER_PA": 0.6,
            "CO_ID_NUMBER_NIT": 0.6,
            "CO_ID_NUMBER_PEP": 0.6,
        }
        
        # Diccionario de umbrales por idioma
        self.thresholds_by_language = {
            "en": self.entity_thresholds_en,
            "es": self.entity_thresholds_es,
        }
        
        self.logger.info("Umbrales de entidades configurados por idioma")

    def get_entity_thresholds(self, language: str) -> Dict[str, float]:
        """Obtiene los umbrales específicos para el idioma seleccionado"""
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando configuración predeterminada (inglés)."
            )
            return self.entity_thresholds_en
        return self.thresholds_by_language.get(language, self.entity_thresholds_en)

    def analyze_text(self, text: str, language: str = "es") -> List[Dict[str, Any]]:
        """Analiza texto y retorna solo las entidades específicas que superen el umbral configurado"""
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language

        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)

        # Primero, validar entidades de tipo PERSON usando el reconocedor personalizado
        person_entities = self.validate_person_entities(text, language)
        
        # Seleccionar el analizador específico para el idioma
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return []

        # Analizar el texto con el analizador para las entidades que no son PERSON
        non_person_entities = [entity for entity in self.target_entities if entity != "PERSON"]
        results = analyzer.analyze(text=text, language=language, entities=non_person_entities)

        # Lista para almacenar todas las entidades filtradas
        filtered_results = []
        
        # Agregar las entidades PERSON ya validadas
        filtered_results.extend(person_entities)

        # Procesar otras entidades que no son PERSON
        for r in results:
            # Filtrar todas las entidades que superen el umbral
            if r.entity_type in self.target_entities and r.score >= thresholds.get(
                r.entity_type, 0.80
            ):
                filtered_results.append(
                    {
                        "entity_type": r.entity_type,
                        "start": r.start,
                        "end": r.end,
                        "score": r.score,
                        "language": language,
                    }
                )

        return filtered_results

    def anonymize_text(self, text: str, language: str = "es") -> str:
        """Anonimiza texto reemplazando solo entidades específicas con puntaje superior al umbral"""
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language

        # Primero, validar entidades de tipo PERSON usando el reconocedor personalizado
        person_entities = self.validate_person_entities(text, language)
        
        # Convertir resultados de personas a formato RecognizerResult para el anonimizador
        person_recognizer_results = []
        for entity in person_entities:
            person_result = RecognizerResult(
                entity_type=entity["entity_type"],
                start=entity["start"],
                end=entity["end"],
                score=entity["score"],
            )
            person_recognizer_results.append(person_result)

        # Seleccionar el analizador específico para el idioma para otras entidades
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return text

        # Analizar el texto para otras entidades
        results = analyzer.analyze(text=text, language=language, entities=self.target_entities)

        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)

        # Filtrar entidades que no son PERSON (ya procesadas por validate_person_entities)
        other_entities_results = []
        for r in results:
            if (
                r.entity_type != "PERSON"
                and r.entity_type in self.target_entities
                and r.score >= thresholds.get(r.entity_type, 0.80)
            ):
                other_entities_results.append(r)

        # Combinar resultados de entidades PERSON y otras entidades
        filtered_results = person_recognizer_results + other_entities_results

        # Anonimizar solo las entidades filtradas
        anonymized = self.anonymizer.anonymize(
            text=text, analyzer_results=filtered_results
        )
        return anonymized.text

    def validate_person_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        """
        Valida las entidades de tipo PERSON utilizando el reconocedor predeterminado de Presidio
        y luego valida con Flair si realmente son nombres de persona.
        """
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language
            
        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)
        person_threshold = thresholds.get("PERSON", 0.1)  # Usar umbral de 0.1 para PERSON
        
        # Seleccionar el analizador específico para el idioma
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return []
            
        # Analizar el texto específicamente para entidades de tipo PERSON
        results = analyzer.analyze(text=text, language=language, entities=["PERSON"])
        
        # Lista para almacenar candidatos que pasan el umbral de Presidio
        candidatos_para_flair = []
        
        # Filtrar solo las entidades que superen el umbral configurado
        for r in results:
            if r.entity_type == "PERSON" and r.score >= person_threshold:
                name_text = text[r.start:r.end].strip()
                
                # Extraer contexto para validación Flair
                inicio_contexto = max(0, r.start - 50)
                fin_contexto = min(len(text), r.end + 50)
                contexto = text[inicio_contexto:fin_contexto]
                
                # Añadir a candidatos para validación con Flair
                candidato = {
                    "entity_type": "PERSON",
                    "nombre": name_text,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "language": language,
                    "contexto": contexto
                }
                candidatos_para_flair.append(candidato)
        
        # Lista para almacenar entidades validadas
        validated_results = []
        
        # Verificar si Flair está disponible
        if FLAIR_DISPONIBLE and candidatos_para_flair:
            try:
                # Crear una instancia del validador Flair
                validador_flair = FlairContextValidator()
                
                # Validar los candidatos con Flair
                for candidato in candidatos_para_flair:
                    nombre = candidato["nombre"]
                    contexto = candidato["contexto"]
                    start = candidato["start"]
                    end = candidato["end"]
                    
                    resultado_validacion = validador_flair.validar_nombre(
                        texto=text, 
                        nombre=nombre, 
                        contexto=contexto,
                        start=start, 
                        end=end
                    )
                    
                    if resultado_validacion["es_valido"]:
                        # Es un nombre válido según Flair
                        validated_results.append({
                            "entity_type": "PERSON",
                            "start": start,
                            "end": end,
                            "score": resultado_validacion["confianza"],
                            "language": language,
                        })
                    
            except Exception as e:
                self.logger.error(f"Error en validación con Flair: {str(e)}")
                # Si falla Flair, usamos los candidatos que pasaron el umbral de Presidio
                for c in candidatos_para_flair:
                    validated_results.append({
                        "entity_type": c["entity_type"],
                        "start": c["start"],
                        "end": c["end"],
                        "score": c["score"],
                        "language": c["language"],
                    })
        else:
            # Si no hay validador Flair disponible, usar los candidatos que pasaron el umbral de Presidio
            for c in candidatos_para_flair:
                validated_results.append({
                    "entity_type": c["entity_type"],
                    "start": c["start"],
                    "end": c["end"],
                    "score": c["score"],
                    "language": c["language"],
                })
        
        return validated_results