from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
from src.utils.logger import setup_logger

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.logger = setup_logger("PresidioService")
        
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
        self.score_threshold = 1.0
    
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
        
        # Registrar todas las entidades encontradas antes del filtrado
        for r in results:
            self.logger.debug(f"Entidad detectada: {r.entity_type}, Score: {r.score}, Texto: {text[r.start:r.end]}")
            
        # Filtrar solo las entidades objetivo con puntaje mayor al umbral
        filtered_results = [r for r in results 
                           if r.entity_type in self.target_entities 
                           and r.score >= self.score_threshold]
        
        # Registrar entidades excluidas (no están en target_entities o tienen score bajo)
        excluded_results = [r for r in results if r not in filtered_results]
        for r in excluded_results:
            reason = "tipo no incluido" if r.entity_type not in self.target_entities else "score bajo"
            self.logger.info(
                f"Entidad excluida: {r.entity_type}, Score: {r.score}, Razón: {reason}, "
                f"Texto: {text[r.start:r.end]}"
            )
            
        # Anonimizar solo las entidades filtradas
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text