from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Entidades específicas a considerar
        self.target_entities = [
            "PERSON", 
            "PHONE_NUMBER", 
            "LOCATION", 
            "TIME", 
            "NRP",  # Cédula
            "EMAIL_ADDRESS",
            "ADDRESS"
        ]
        
        # Umbral de puntuación fijo
        self.score_threshold = 0.95
    
    def analyze_text(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """Analiza texto y retorna solo las entidades específicas con su puntaje"""
        results = self.analyzer.analyze(text=text, language=language)
        # Filtrar solo las entidades objetivo
        filtered_results = [r for r in results if r.entity_type in self.target_entities]
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in filtered_results]
    
    def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando solo entidades específicas con puntaje superior al umbral"""
        results = self.analyzer.analyze(text=text, language=language)
        # Filtrar solo las entidades objetivo con puntaje mayor al umbral
        filtered_results = [r for r in results 
                           if r.entity_type in self.target_entities 
                           and r.score >= self.score_threshold]
        
        # Anonimizar solo las entidades filtradas
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text