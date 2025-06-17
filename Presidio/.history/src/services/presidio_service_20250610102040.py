from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
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
        results = self.analyzer.analyze(text=text, language=language)
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in results]
    
    def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        results = self.analyzer.analyze(text=text, language=language)
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
      def anonymize_specific_entities(self, text: str, language: str = 'en', 
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
        try:
            # Validar idioma (puede ser 'en', 'es', etc.)
            supported_languages = ['en', 'es']  # Añade más idiomas según sea necesario
            if language not in supported_languages:
                language = 'en'  # Usar inglés por defecto si el idioma no es compatible
            
            # Usar umbrales personalizados si se proporcionan, de lo contrario usar los predeterminados
            thresholds = self.entities_thresholds.copy()
            if custom_thresholds:
                thresholds.update(custom_thresholds)
            
            # Analizar el texto para encontrar todas las entidades
            all_results = self.analyzer.analyze(text=text, language=language)
            
            # Si no hay resultados, verificar si hay suficientes datos
            if not all_results and len(text) < 10:
                # El texto es muy corto para analizar efectivamente
                return text
                
            # Filtrar solo las entidades que queremos anonimizar y que superen su umbral específico
            filtered_results = [r for r in all_results 
                               if r.entity_type in thresholds and 
                               r.score >= thresholds[r.entity_type]]
            
            # Anonimizar solo las entidades filtradas
            if filtered_results:
                anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
                return anonymized.text
            else:
                # No se encontraron entidades que cumplan con los criterios
                # Intentar con un umbral más bajo para diagnóstico
                any_entities = [r for r in all_results if r.entity_type in thresholds]
                if any_entities:
                    # Hay entidades pero no cumplen con el umbral
                    return text
                else:
                    # No se encontraron entidades en absoluto
                    return text
        except Exception as e:
            # Registrar el error pero devolver el texto original
            import logging
            logging.error(f"Error en anonymize_specific_entities: {str(e)}")
            return text