from typing import List, Dict, Any
from src.presidio.engine import PresidioEngine
from src.services.file_service import FileService
from src.utils.logger import setup_logger

class AnonymizationService:
    """
    Servicio de alto nivel para análisis y anonimización de texto y archivos.
    Coordina entre el motor de Presidio y el servicio de archivos.
    """
    
    def __init__(self, presidio_engine: PresidioEngine, file_service: FileService):
        self.presidio_engine = presidio_engine
        self.file_service = file_service
        self.logger = setup_logger("AnonymizationService")
        self.default_language = "es"
        self.supported_languages = ["en", "es"]
        self.language_names = {"en": "inglés", "es": "español"}

    def get_language_name(self, language_code: str) -> str:
        """Obtiene el nombre descriptivo del idioma"""
        return self.language_names.get(language_code, f"desconocido ({language_code})")

    def normalize_language(self, language: str = None) -> str:
        """Normaliza y valida el código de idioma"""
        language = (language or self.default_language).lower()
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            return self.default_language
        return language

    def analyze_text(self, text: str, language: str = None) -> List[Dict[str, Any]]:
        """Analiza texto para identificar entidades PII"""
        language = self.normalize_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Analizando texto en {language} ({language_name})")
        self.logger.info(f"Longitud del texto: {len(text)} caracteres")
        self.logger.info(f"Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        # Delegar al motor de Presidio
        results = self.presidio_engine.analyze_text(text, language)
        
        # Añadir el texto específico de cada entidad a los resultados
        for entity in results:
            entity['text'] = text[entity['start']:entity['end']]
        
        self.logger.info(f"Total entidades encontradas: {len(results)}")
        for idx, entity in enumerate(results[:5]):  # Limitar a 5 para no saturar los logs
            self.logger.info(f"  Entidad {idx+1}: {entity['entity_type']} - '{entity['text']}' (score: {entity['score']:.2f})")
        if len(results) > 5:
            self.logger.info(f"  ... y {len(results)-5} entidades más")
            
        return results

    def anonymize_text(self, text: str, language: str = None) -> str:
        """Anonimiza texto reemplazando entidades PII"""
        language = self.normalize_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Anonimizando texto en {language} ({language_name})")
        self.logger.info(f"Longitud del texto: {len(text)} caracteres")
        self.logger.info(f"Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        # Delegar al motor de Presidio
        anonymized_text = self.presidio_engine.anonymize_text(text, language)
        
        self.logger.info(f"Longitud del texto anonimizado: {len(anonymized_text)} caracteres")
        self.logger.info(f"Contenido anonimizado: '{anonymized_text[:100]}{'...' if len(anonymized_text) > 100 else ''}'")
        
        return anonymized_text

    def analyze_file(self, file_content: bytes, filename: str, language: str = None) -> Dict[str, Any]:
        """Analiza un archivo para identificar entidades PII"""
        language = self.normalize_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Analizando archivo: {filename} en {language} ({language_name})")
        
        # Extraer texto del archivo
        extracted_text = self.file_service.process_file(file_content, filename)
        self.logger.info(f"Texto extraído: {len(extracted_text)} caracteres")
        self.logger.info(f"Contenido: '{extracted_text[:100]}{'...' if len(extracted_text) > 100 else ''}'")
        
        # Analizar el texto extraído
        entities = self.analyze_text(extracted_text, language)
        
        return {
            'filename': filename,
            'extracted_text': extracted_text,
            'entities': entities,
            'language': language,
            'language_name': language_name,
            'total_entities': len(entities)
        }

    def anonymize_file(self, file_content: bytes, filename: str, language: str = None) -> Dict[str, Any]:
        """Anonimiza un archivo"""
        language = self.normalize_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Anonimizando archivo: {filename} en {language} ({language_name})")
        
        # Extraer texto del archivo
        extracted_text = self.file_service.process_file(file_content, filename)
        self.logger.info(f"Texto extraído: {len(extracted_text)} caracteres")
        self.logger.info(f"Contenido original: '{extracted_text[:100]}{'...' if len(extracted_text) > 100 else ''}'")
        
        # Anonimizar el texto extraído
        anonymized_text = self.anonymize_text(extracted_text, language)
        
        return {
            'filename': filename,
            'original_text': extracted_text,
            'anonymized_text': anonymized_text,
            'language': language,
            'language_name': language_name
        }
        
    def preview_anonymization(self, text: str, language: str = None) -> Dict[str, Any]:
        """Previsualiza la anonimización sin aplicarla"""
        language = self.normalize_language(language)
        language_name = self.get_language_name(language)
        
        self.logger.info(f"Previsualizando anonimización en {language} ({language_name})")
        self.logger.info(f"Longitud del texto: {len(text)} caracteres")
        self.logger.info(f"Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        # Analizar el texto para detectar entidades
        entities = self.analyze_text(text, language)
        
        return {
            'texto_completo': text,
            'entidades_detectadas': entities,
            'total_entidades': len(entities),
            'idioma': language,
            'nombre_idioma': language_name
        }