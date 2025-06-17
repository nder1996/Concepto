from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Entidades específicas a anonimizar
        self.target_entities = [
            "PERSON", 
            "PHONE_NUMBER", 
            "LOCATION", 
            "TIME", 
            "NRP", # Número de cédula/documento (Colombian ID)
            "EMAIL_ADDRESS",
            "ADDRESS"
        ]
        
        # Umbral de puntuación fijo
        self.score_threshold = 0.65
    
    def analyze_text(self, text: str, language: str = 'es') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades encontradas"""
        results = self.analyzer.analyze(text=text, language=language)
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in results]
    
    def anonymize_text(self, text: str, language: str = 'es') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        results = self.analyzer.analyze(text=text, language=language)
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
      def anonymize_selective(self, text: str, language: str = 'es') -> str:
        """
        Anonimiza SOLO entidades específicas de Microsoft Presidio 
        basándose en un umbral de puntuación fijo.
        
        Solo se anonimizan: PERSON, PHONE, LOCATION, TIME, CEDULA, EMAIL, ADDRESS
        """
        try:
            # Validar el idioma (es, en, etc.)
            supported_languages = ['es', 'en']  # Añadir más idiomas según sea necesario
            if language not in supported_languages:
                import logging
                logging.warning(f"Idioma '{language}' no soportado. Usando español por defecto.")
                language = 'es'
            
            # Analizar el texto para encontrar todas las entidades
            all_results = self.analyzer.analyze(text=text, language=language)
            
            # Filtrar solo las entidades objetivo con puntaje mayor al umbral
            filtered_results = [
                result for result in all_results 
                if result.entity_type in self.target_entities and result.score >= self.score_threshold
            ]
            
            # Si no hay resultados que cumplan los criterios, retornar el texto original
            if not filtered_results:
                return text
            
            # Anonimizar solo las entidades filtradas
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
            
            return anonymized.text
            
        except Exception as e:
            import logging
            logging.error(f"Error en anonymize_selective: {str(e)}")
            return text  # En caso de error, devolver el texto original