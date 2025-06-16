from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import spacy
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.utils.logger import setup_logger
from src.config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, SPACY_MODELS

# Importar los reconocedores personalizados desde el módulo centralizado
from src.services.presidio.recognizers import EmailRecognizer, PhoneRecognizer, ColombianIDRecognizer

class PresidioNLPService:
    """
    Servicio para la inicialización y gestión de los motores NLP de Presidio.
    Este servicio se encarga de configurar los modelos spaCy y los reconocedores de entidades.
    """
    
    def __init__(self):
        self.logger = setup_logger("PresidioNLPService")
        self.logger.info("Inicializando servicio de NLP para Presidio...")
        
        # Utilizar configuración centralizada
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        
        # Inicializar los analizadores para cada idioma
        self.analyzers = {}
        self.nlp_engines = {}
        
        self._initialize_engines()
        
    def _initialize_engines(self):
        """Inicializa los motores NLP y analizadores para cada idioma soportado"""
        try:
            # Configurar para español
            self.logger.info(f"Cargando modelo {SPACY_MODELS['es']} para español...")
            nlp_config_es = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "es", "model_name": SPACY_MODELS['es']}],
            }
            nlp_provider_es = NlpEngineProvider(nlp_configuration=nlp_config_es)
            nlp_engine_es = nlp_provider_es.create_engine()
            self.nlp_engines['es'] = nlp_engine_es

            # Configurar para inglés
            self.logger.info(f"Cargando modelo {SPACY_MODELS['en']} para inglés...")
            nlp_config_en = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": SPACY_MODELS['en']}],
            }
            nlp_provider_en = NlpEngineProvider(nlp_configuration=nlp_config_en)
            nlp_engine_en = nlp_provider_en.create_engine()
            self.nlp_engines['en'] = nlp_engine_en
            
            # Crear los analizadores para cada idioma
            self._setup_analyzers()
            
            self.logger.info("Inicialización de motores NLP completada con éxito")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar motores NLP: {str(e)}")
            raise
            
    def _setup_analyzers(self):
        """Configurar los analizadores con los reconocedores apropiados para cada idioma"""
        # Para español
        self.logger.info("Configurando analizador para español...")
        registry_es = RecognizerRegistry()
        registry_es.load_predefined_recognizers(nlp_engine=self.nlp_engines['es'])

        # Registrar reconocedores personalizados para español
        self._register_custom_recognizers(registry_es, 'es')
        self.analyzers['es'] = AnalyzerEngine(
            registry=registry_es, 
            nlp_engine=self.nlp_engines['es']
        )

        # Para inglés
        self.logger.info("Configurando analizador para inglés...")
        registry_en = RecognizerRegistry()
        registry_en.load_predefined_recognizers(nlp_engine=self.nlp_engines['en'])

        # Registrar reconocedores personalizados para inglés
        self._register_custom_recognizers(registry_en, 'en')
        self.analyzers['en'] = AnalyzerEngine(
            registry=registry_en, 
            nlp_engine=self.nlp_engines['en']
        )
        
    def _register_custom_recognizers(self, registry, language):
        """Registra reconocedores personalizados según el idioma"""
        if language == 'es':
            # Registrar reconocedores personalizados para español
            self.logger.info("Registrando reconocedores personalizados para español...")
            
            # Reconocedor de correo electrónico
            self.logger.info("Registrando reconocedor de correos electrónicos...")
            email_recognizer_es = EmailRecognizer(supported_language="es")
            registry.add_recognizer(email_recognizer_es)
            
            # Reconocedor de teléfono
            self.logger.info("Registrando reconocedor de números telefónicos...")
            phone_recognizer_es = PhoneRecognizer(supported_language="es")
            registry.add_recognizer(phone_recognizer_es)
            
            # Reconocedor de documentos colombianos (solo para español)
            self.logger.info("Registrando reconocedor de documentos de identidad colombianos...")
            id_recognizer_es = ColombianIDRecognizer(supported_language="es")
            registry.add_recognizer(id_recognizer_es)
            
            # Log de tipos de documentos soportados
            self.logger.info("Tipos de documentos colombianos soportados:")
            self.logger.info("- Cédula de Ciudadanía (CC)")
            self.logger.info("- Tarjeta de Identidad (TI)")
            self.logger.info("- Cédula de Extranjería (CE)")
            self.logger.info("- Registro Civil (RC)")
            self.logger.info("- Pasaporte (PA)")
            self.logger.info("- NIT")
            self.logger.info("- Permiso Especial de Permanencia (PEP)")
            
        elif language == 'en':
            # Registrar reconocedores personalizados para inglés
            self.logger.info("Registrando reconocedores personalizados para inglés...")
            
            # Reconocedor de correo electrónico
            self.logger.info("Registrando reconocedor de correos electrónicos...")
            email_recognizer_en = EmailRecognizer(supported_language="en")
            registry.add_recognizer(email_recognizer_en)
            
            # Reconocedor de teléfono
            self.logger.info("Registrando reconocedor de números telefónicos...")
            phone_recognizer_en = PhoneRecognizer(supported_language="en")
            registry.add_recognizer(phone_recognizer_en)
    
    def get_analyzer(self, language: str):
        """
        Obtiene el analizador para el idioma especificado
        
        Args:
            language: Código de idioma ('es', 'en')
            
        Returns:
            AnalyzerEngine: El analizador para el idioma especificado
        """
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language
            
        return self.analyzers.get(language)
        
    def get_nlp_engine(self, language: str):
        """
        Obtiene el motor NLP para el idioma especificado
        
        Args:
            language: Código de idioma ('es', 'en')
            
        Returns:
            El motor NLP para el idioma especificado
        """
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            language = self.default_language
            
        return self.nlp_engines.get(language)
