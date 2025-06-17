from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

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
    
    def quemar_por_score(self, text: str, person_score: float = 0.5, phone_score: float = 0.5, language: str = 'es') -> str:
        """
        Quema (reemplaza con valores fijos) solo entidades PERSON y PHONE_NUMBER 
        que superen el score especificado
        """
        # Analizar el texto
        results = self.analyzer.analyze(text=text, language=language)
        
        # Filtrar solo PERSON y PHONE_NUMBER que superen el score indicado
        filtered_results = []
        for r in results:
            if r.entity_type == "PERSON" and r.score >= person_score:
                filtered_results.append(r)
            elif r.entity_type == "PHONE_NUMBER" and r.score >= phone_score:
                filtered_results.append(r)
        
        # Configurar reemplazo fijo
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "XXXX"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "XXXX"})
        }
        
        # Anonimizar con resultados filtrados y operadores fijos
        anonymized = self.anonymizer.anonymize(
            text=text, 
            analyzer_results=filtered_results,
            operators=operators
        )
        
        return anonymized.text