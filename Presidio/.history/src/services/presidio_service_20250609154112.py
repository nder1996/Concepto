from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

class PresidioService:
    def __init__(self):
        # Crear un registro personalizado
        registry = RecognizerRegistry()
        # Registrar los reconocedores predeterminados
        registry.load_predefined_recognizers()
        
        # Reemplazar el reconocedor de PERSON con uno personalizado
        # que devuelve un score fijo de 0.9
        self.person_score = 0.9
        person_recognizer = self._create_fixed_score_person_recognizer()
        registry.add_recognizer(person_recognizer)
        
        # Inicializar el analizador con el registro personalizado
        self.analyzer = AnalyzerEngine(registry=registry)
        self.anonymizer = AnonymizerEngine()
        
    def _create_fixed_score_person_recognizer(self):
        """Crea un reconocedor personalizado para PERSON con score fijo"""
        from presidio_analyzer.predefined_recognizers import SpacyRecognizer
        
        # Heredar del reconocedor de SpaCy para mantener la funcionalidad
        class FixedScorePersonRecognizer(SpacyRecognizer):
            def analyze(self, text, entities=None, nlp_artifacts=None):
                results = super().analyze(text, entities, nlp_artifacts)
                # Filtrar solo resultados de tipo PERSON y establecer score fijo
                person_results = []
                for result in results:
                    if result.entity_type == "PERSON":
                        result.score = self.person_score
                        person_results.append(result)
                return person_results
        
        recognizer = FixedScorePersonRecognizer(supported_entities=["PERSON"])
        recognizer.person_score = self.person_score
        return recognizer
        
    def analyze_text(self, text: str, language: str = 'en', score_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Analiza texto usando el reconocedor personalizado para PERSON"""
        results = self.analyzer.analyze(
            text=text, 
            language=language,
            score_threshold=score_threshold
        )
        
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in results]
        
    def anonymize_text(self, text: str, language: str = 'en', score_threshold: float = 0.5) -> str:
        """Anonimiza texto usando el reconocedor personalizado para PERSON"""
        results = self.analyzer.analyze(
            text=text, 
            language=language,
            score_threshold=score_threshold
        )
        
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text