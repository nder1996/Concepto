from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        # Lista de palabras seguras que no deben ser anonimizadas
        self.safe_words = [
            "BootsFaces", 
            "PrimeFaces",
            "JavaFaces",
            "RichFaces",
            "IceFaces",
            # Añade más palabras seguras según sea necesario
        ]
    
    def filter_false_positives(self, results, text):
        """Filtra resultados para remover falsos positivos basados en palabras seguras"""
        filtered_results = []
        for r in results:
            # Extraer el texto detectado
            detected_text = text[r.start:r.end]
            
            # Verificar si es una palabra segura
            is_safe_word = detected_text in self.safe_words
            
            # Aplicar reglas específicas basadas en tipo de entidad
            if r.entity_type == "IN_PAN" and (is_safe_word or not detected_text.isdigit()):
                # Para números PAN, filtrar si es una palabra segura o si no contiene solo dígitos
                self.analyzer.logger.debug(f"Filtrado falso positivo PAN: {detected_text}")
                continue
            
            # Si pasó todos los filtros, añadirlo a los resultados
            filtered_results.append(r)
            
        return filtered_results
    
    def analyze_text(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades encontradas"""
        results = self.analyzer.analyze(text=text, language=language)
        
        # Filtrar falsos positivos
        filtered_results = self.filter_false_positives(results, text)
        
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in filtered_results]
      def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        results = self.analyzer.analyze(text=text, language=language)
        
        # Filtrar falsos positivos antes de anonimizar
        filtered_results = self.filter_false_positives(results, text)
        
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text