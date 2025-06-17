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
            "DATE_TIME", 
            "NRP",  # Cédula
            "EMAIL_ADDRESS",
            "ADDRESS"
        ]
        
        # Umbrales específicos para cada tipo de entidad
        self.entity_thresholds = {
            "PERSON": 0.85,
            "PHONE_NUMBER": 0.75,
            "LOCATION": 0.80,
            "TIME": 0.70,
            "NRP": 0.90,
            "EMAIL_ADDRESS": 0.95,
            "ADDRESS": 0.85
        }

    def analyze_text(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """Analiza texto y retorna solo las entidades específicas con su puntaje"""
        results = self.analyzer.analyze(text=text, language=language)
        
        # Registrar todas las entidades detectadas originalmente
        self.logger.info(f"Total de entidades detectadas: {len(results)}")
        for r in results:
            self.logger.info(
                f"Entidad detectada: {r.entity_type}, "
                f"Score: {r.score}, Texto: {text[r.start:r.end]}"
            )
        
        # Filtrar solo las entidades objetivo
        filtered_results = [r for r in results if r.entity_type in self.target_entities]
        
        # Registrar las entidades que SÍ se consideran relevantes
        self.logger.info(f"Entidades consideradas relevantes: {len(filtered_results)}")
        for r in filtered_results:
            self.logger.info(
                f"Entidad detectada y considerada: {r.entity_type}, "
                f"Score: {r.score}, Texto: {text[r.start:r.end]}"
            )
        
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in filtered_results]

    def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando solo entidades específicas con puntaje superior al umbral"""
        results = self.analyzer.analyze(text=text, language=language)
        
        # Filtrar solo las entidades objetivo con puntaje mayor al umbral específico de cada entidad
        filtered_results = [r for r in results 
                          if r.entity_type in self.target_entities 
                          and r.score >= self.entity_thresholds.get(r.entity_type, 0.80)]
        
        # Registrar todas las entidades detectadas originalmente
        self.logger.info(f"Total de entidades detectadas: {len(results)}")
        for r in results:
            self.logger.info(
                f"Entidad detectada: {r.entity_type}, "
                f"Score: {r.score}, Texto: {text[r.start:r.end]}"
            )
        
        # Registrar las entidades que SÍ serán anonimizadas
        self.logger.info(f"Entidades que serán anonimizadas: {len(filtered_results)}")
        for r in filtered_results:
            threshold = self.entity_thresholds.get(r.entity_type, 0.80)
            self.logger.info(
                f"Entidad detectada y anonimizada: {r.entity_type}, "
                f"Score: {r.score} (umbral: {threshold}), Texto: {text[r.start:r.end]}"
            )
        
        # Anonimizar solo las entidades filtradas
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text