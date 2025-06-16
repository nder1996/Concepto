from typing import List, Dict, Any, Optional
import logging
from src.services.presidio.core_presidio_service import CorePresidioService
from src.services.file_processor import FileProcessor
from src.config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, LANGUAGE_NAMES


class PresidioOrchestratorService:
    """
    Servicio orquestador que actúa como intermediario entre el controlador y los servicios
    de procesamiento de Presidio. Este servicio se encarga de la validación, logging y lógica de negocio,
    mientras que el controlador sólo se ocupa de recibir solicitudes y enviar respuestas.
    """

    def __init__(self, entity_service: CorePresidioService, file_processor: FileProcessor, logger: logging.Logger):
        """
        Inicializa el servicio orquestador
        
        Args:
            entity_service: Servicio unificado de Presidio para análisis y anonimización
            file_processor: Procesador de archivos
            logger: Logger centralizado para registro de eventos
        """
        self.entity_service = entity_service
        self.file_processor = file_processor
        self.logger = logger
        self.default_language = DEFAULT_LANGUAGE
        self.supported_languages = SUPPORTED_LANGUAGES
        self.language_names = LANGUAGE_NAMES

    def get_language_name(self, language_code):
        """
        Devuelve el nombre descriptivo del idioma en base al código
        
        Args:
            language_code: El código de idioma (ej: 'es', 'en')
            
        Returns:
            El nombre descriptivo del idioma
        """
        return self.language_names.get(language_code, f"desconocido ({language_code})")

    def validate_language(self, language: Optional[str]) -> str:
        """
        Valida y normaliza el código de idioma
        
        Args:
            language: Código de idioma proporcionado por el usuario
            
        Returns:
            Código de idioma validado y normalizado
        """
        if not language:
            return self.default_language
            
        language = language.lower()
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            return self.default_language
            
        return language

    def analyze_text(self, text: str, language: Optional[str], entities: List[str] = None) -> Dict[str, Any]:
        """
        Analiza texto para detectar entidades PII
        
        Args:
            text: Texto a analizar
            language: Idioma del texto
            entities: Lista de tipos de entidades a buscar (opcional)
            
        Returns:
            Diccionario con resultados del análisis y metadatos
        """
        if not text or len(text.strip()) == 0:
            self.logger.warning("Texto vacío enviado para análisis")
            return {
                'results': [],
                'language': self.default_language,
                'language_name': self.get_language_name(self.default_language),
                'total_entities': 0
            }
            
        # Validar idioma
        language = self.validate_language(language)
        language_name = self.get_language_name(language)
          # Log simplificado con formato JSON
        import json
        request_info = {
            "endpoint": "analyze_text",
            "language": language,
            "language_name": language_name,
            "text_length": len(text),
            "sample": text[:50] + ('...' if len(text) > 50 else '')
        }
        self.logger.info(f"[Request] {json.dumps(request_info)}")
        
        try:
            # Realizar análisis con el servicio unificado
            start_time = __import__('time').time()
            results = self.entity_service.analyze_text(text, language=language, entities=entities)
            exec_time = round((__import__('time').time() - start_time) * 1000, 2)
            
            # Log de respuesta simplificado
            response_info = {
                "status": "success",
                "exec_time_ms": exec_time,
                "total_entities": len(results)
            }
            self.logger.info(f"[Response] {json.dumps(response_info)}")
            for idx, entity in enumerate(results[:5]):  # Limitar a 5 para no saturar logs
                self.logger.info(
                    f"  Entidad {idx+1}: {entity['entity_type']} - '{entity['text']}' (score: {entity['score']:.2f})"
                )
            if len(results) > 5:
                self.logger.info(f"  ... y {len(results)-5} entidades más")
            
            return {
                'results': results,
                'language': language,
                'language_name': language_name,
                'total_entities': len(results)
            }
        except Exception as e:
            self.logger.error(f"Error en análisis: {str(e)}")
            raise
    
    def anonymize_text(self, text: str, language: Optional[str], entities: List[str] = None) -> Dict[str, Any]:
        """
        Anonimiza texto identificando y reemplazando entidades PII
        
        Args:
            text: Texto a anonimizar
            language: Idioma del texto
            entities: Lista de tipos de entidades a anonimizar (opcional)
            
        Returns:
            Diccionario con texto anonimizado y metadatos
        """
        if not text or len(text.strip()) == 0:
            self.logger.warning("Texto vacío enviado para anonimización")
            return {
                'anonymized_text': '',
                'items': [],
                'language': self.default_language,
                'language_name': self.get_language_name(self.default_language),
                'total_items': 0
            }
            
        # Validar idioma
        language = self.validate_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Request de anonimización:")
        self.logger.info(f"- Idioma: {language} ({language_name})")
        self.logger.info(f"- Longitud del texto: {len(text)} caracteres")
        self.logger.info(f"- Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        try:
            # Realizar anonimización con el servicio unificado
            result = self.entity_service.anonymize_text(text, language=language, entities=entities)
            
            self.logger.info("Resultado de la anonimización:")
            self.logger.info(f"- Total entidades anonimizadas: {len(result['items'])}")
            
            return {
                'anonymized_text': result['text'],
                'items': result['items'],
                'language': language,
                'language_name': language_name,
                'total_items': len(result['items'])
            }
        except Exception as e:
            self.logger.error(f"Error en anonimización: {str(e)}")
            raise
    
    def process_file(self, file_content: bytes, filename: str) -> str:
        """
        Procesa un archivo para extraer su contenido como texto
        
        Args:
            file_content: Contenido binario del archivo
            filename: Nombre del archivo
            
        Returns:
            Texto extraído del archivo
        """
        try:
            self.logger.info(f"Procesando archivo: {filename}")
            text = self.file_processor.process_file(file_content, filename)
            self.logger.info(f"Texto extraído: {len(text)} caracteres")
            return text
        except Exception as e:
            self.logger.error(f"Error al procesar archivo {filename}: {str(e)}")
            raise
    
    def preview_anonymization(self, text: str, language: Optional[str]) -> Dict[str, Any]:
        """
        Previsualiza resultados de análisis y anonimización para un texto
        
        Args:
            text: Texto a previsualizar
            language: Idioma del texto
            
        Returns:
            Diccionario con resultados de análisis y anonimización
        """
        if not text or len(text.strip()) == 0:
            self.logger.warning("Texto vacío enviado para previsualización")
            return {
                'analysis': [],
                'anonymization': {'text': '', 'items': []},
                'language': self.default_language,
                'language_name': self.get_language_name(self.default_language)
            }
        
        # Validar idioma
        language = self.validate_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Request de previsualización:")
        self.logger.info(f"- Idioma: {language} ({language_name})")
        self.logger.info(f"- Longitud del texto: {len(text)} caracteres")
        
        try:
            # Analizar el texto
            analysis_results = self.entity_service.analyze_text(text, language=language)
            
            # Realizar la anonimización
            anonymization_result = self.entity_service.anonymize_text(text, language=language)
            
            self.logger.info("Resultado de la previsualización:")
            self.logger.info(f"- Total entidades encontradas: {len(analysis_results)}")
            self.logger.info(f"- Total entidades anonimizadas: {len(anonymization_result['items'])}")
            
            return {
                'analysis': analysis_results,
                'anonymization': {
                    'text': anonymization_result['text'],
                    'items': anonymization_result['items']
                },
                'language': language,
                'language_name': language_name
            }
        except Exception as e:
            self.logger.error(f"Error en previsualización: {str(e)}")
            raise
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del servicio
        
        Returns:
            Diccionario con información sobre el estado del servicio
        """
        try:
            service_status = self.entity_service.get_service_status()
            return {
                'status': 'up',
                'services': service_status
            }
        except Exception as e:
            self.logger.error(f"Error al obtener estado del servicio: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_recognizers_info(self) -> Dict[str, Any]:
        """
        Devuelve información sobre los tipos de entidades que pueden ser reconocidas
        por los reconocedores personalizados implementados.
        
        Returns:
            Diccionario con información sobre reconocedores personalizados
        """
        from src.services.presidio.recognizers.recognizer_co_identity_number import ColombianIDRecognizer
        from src.services.presidio.recognizers.recognizer_email import EmailRecognizer
        from src.services.presidio.recognizers.recognizer_phone import PhoneRecognizer
        
        self.logger.info("Solicitando información de reconocedores personalizados")
        
        # Instanciar los reconocedores para obtener información
        colombian_id_recognizer = ColombianIDRecognizer()
        email_recognizer = EmailRecognizer()
        phone_recognizer = PhoneRecognizer()
        
        recognizers = [
            {
                "name": colombian_id_recognizer.name,
                "entity_type": colombian_id_recognizer.supported_entities[0],
                "supported_language": colombian_id_recognizer.supported_language,
                "description": "Reconoce documentos de identidad colombianos (CC, TI, CE, RC, PA, NIT, PEP)"
            },
            {
                "name": email_recognizer.name,
                "entity_type": email_recognizer.supported_entities[0],
                "supported_language": email_recognizer.supported_language,
                "description": "Reconoce direcciones de correo electrónico con alta precisión"
            },
            {
                "name": phone_recognizer.name,
                "entity_type": phone_recognizer.supported_entities[0],
                "supported_language": phone_recognizer.supported_language,
                "description": "Reconoce números telefónicos latinoamericanos en diversos formatos"
            }
        ]
        
        return {
            'recognizers': recognizers,
            'total_recognizers': len(recognizers)
        }
    
    def generate_recognizer_examples(self) -> Dict[str, Any]:
        """
        Genera ejemplos para los tipos de entidades que pueden ser reconocidas
        por los reconocedores personalizados implementados.
        
        Returns:
            Diccionario con ejemplos para cada tipo de entidad
        """
        self.logger.info("Solicitando ejemplos de reconocedores personalizados")
        
        examples = {
            "CO_ID_NUMBER": [
                "C.C. 1234567890",
                "Mi cédula es 1234567890",
                "Tarjeta de identidad 1234567890",
                "NIT 900.123.456-7",
                "Mi registro civil es NUIP 1234567890",
                "Pasaporte: ABC123456",
                "Cédula de extranjería 123456"
            ],
            "EMAIL_ADDRESS": [
                "correo@ejemplo.com",
                "usuario.nombre@empresa.com.co",
                "mi-correo+etiqueta@dominio.net",
                "Contacto: info@miempresa.org"
            ],
            "PHONE_NUMBER": [
                "+57 300 123 4567",
                "(1) 2345678",
                "Celular: 3001234567",
                "Mi número es 318-765-4321",
                "+57 (4) 513 9876",
                "Fijo: 6042345678"
            ]
        }
        
        return {
            'examples': examples,
            'total_entity_types': len(examples)
        }
