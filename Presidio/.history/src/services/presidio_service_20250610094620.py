from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any, Optional, Union

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
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
      def filter_entities(self, 
                        text: str, 
                        entity_types: Optional[Union[List[str], str]] = None, 
                        min_score: float = 0.0, 
                        language: str = 'en') -> Dict[str, Any]:
        """
        Filtra las entidades por tipo y puntaje mínimo, y puede anonimizar el texto si se solicita.
        
        Args:
            text (str): Texto a analizar
            entity_types (Union[List[str], str], optional): Tipo(s) de entidad a filtrar (p.ej., 'PERSON', 'EMAIL_ADDRESS', etc.)
                                                           Si es None, incluye todas las entidades.
            min_score (float, optional): Puntaje mínimo para filtrar entidades (0.0 a 1.0)
            language (str, optional): Idioma del texto. Por defecto 'en'.
            
        Returns:
            Dict[str, Any]: Diccionario con el texto original, entidades filtradas y texto anonimizado
        """
        try:
            # Obtener todas las entidades
            all_entities = self.analyze_text(text=text, language=language)
            
            # Convertir entity_types a lista si es una cadena
            if entity_types and isinstance(entity_types, str):
                entity_types = [entity_types]
            
            # Filtrar por tipo de entidad y puntaje
            filtered_entities = []
            for entity in all_entities:
                if (entity_types is None or entity['entity_type'] in entity_types) and entity['score'] >= min_score:
                    filtered_entities.append(entity)
            
            # Extraer los fragmentos de texto correspondientes a cada entidad filtrada
            entity_texts = []
            for entity in filtered_entities:
                start, end = entity['start'], entity['end']
                entity_texts.append({
                    'entity_type': entity['entity_type'],
                    'score': entity['score'],
                    'text': text[start:end]
                })
          # Anonimizar solo las entidades filtradas si existen
        anonymized_text = ""
        if filtered_entities:
            # Ejecutar el análisis nuevamente y filtrar los resultados originales
            # en lugar de recrear los objetos RecognizerResult
            all_results = self.analyzer.analyze(text=text, language=language)
            
            # Filtrar los resultados originales basados en las entidades filtradas
            filtered_results = []
            for result in all_results:
                for entity in filtered_entities:
                    if (result.entity_type == entity['entity_type'] and 
                        result.start == entity['start'] and 
                        result.end == entity['end']):
                        filtered_results.append(result)
                        break
            
            if filtered_results:
                anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
                anonymized_text = anonymized.text
            else:
                anonymized_text = text
        else:
            anonymized_text = text  # No hay cambios si no hay entidades filtradas
        
        # Construir respuesta
        return {
            'original_text': text,
            'filtered_entities': filtered_entities,
            'entity_texts': entity_texts,
            'anonymized_text': anonymized_text
        }