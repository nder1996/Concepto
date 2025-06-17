from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any, Set
import re
from src.utils.filter_lists import (
    TECH_TERMS, PERSON_SAFE_TERMS, LOCATION_SAFE_TERMS, NRP_SAFE_TERMS,
    PAN_SAFE_TERMS, DATETIME_SAFE_TERMS, URL_SAFE_TERMS,
    CONFIDENCE_THRESHOLDS, REGEX_FILTERS, ORGANIZATIONS
)

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Usar los umbrales desde el módulo filter_lists
        self.min_score_threshold = CONFIDENCE_THRESHOLDS
        
        # Crear diccionario de términos seguros por tipo de entidad
        self.safe_terms_by_type = {
            "PERSON": set(PERSON_SAFE_TERMS),
            "LOCATION": set(LOCATION_SAFE_TERMS),
            "NRP": set(NRP_SAFE_TERMS),
            "IN_PAN": set(PAN_SAFE_TERMS),
            "DATE_TIME": set(DATETIME_SAFE_TERMS),
            "URL": set(URL_SAFE_TERMS),
            # También se pueden añadir más tipos aquí
        }
        
        # Términos técnicos generales (para cualquier tipo)
        self.tech_terms = set(TECH_TERMS)
        
        # Organizaciones conocidas
        self.organizations = set(ORGANIZATIONS)
        
        # Regex patterns por tipo de entidad
        self.regex_filters = REGEX_FILTERS
        
        # Construir expresiones regulares para términos técnicos
        # Combinamos términos técnicos y organizaciones para la expresión general
        all_terms = list(self.tech_terms) + list(self.organizations)
        self.tech_pattern = re.compile(r'\b(' + '|'.join(re.escape(term) for term in all_terms) + r')\b', 
                                      re.IGNORECASE)
    
    def _filter_false_positives(self, results, text):
        """Filtra resultados para eliminar falsos positivos basados en múltiples criterios"""
        filtered_results = []
        
        for r in results:
            detected_text = text[r.start:r.end]
            entity_type = r.entity_type
            score = r.score
            
            # 1. Filtrar por umbral de confianza específico por tipo de entidad
            threshold = self.min_score_threshold.get(entity_type, self.min_score_threshold["DEFAULT"])
            if score < threshold:
                continue
                
            # 2. Filtrar términos técnicos usando expresiones regulares
            if self.tech_pattern.search(detected_text):
                continue
                
            # 3. Reglas específicas por tipo de entidad
            if entity_type == "IN_PAN":
                # Para números PAN, filtrar si no tiene formato válido (debe tener suficientes dígitos)
                if not re.search(r'\d{6,}', detected_text):
                    continue
                    
            elif entity_type == "PERSON":
                # Para personas, verificar si no parece un nombre completo típico
                if not re.search(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)+$', detected_text):
                    # Si es una frase larga o no tiene formato de nombre, es probable que sea un falso positivo
                    if len(detected_text.split()) > 2 or " de " in detected_text.lower():
                        continue
                        
            elif entity_type == "LOCATION":
                # Para ubicaciones, filtrar frases comunes como "en el", "la lógica"
                if re.match(r'^(el|la|los|las|en el|en la|en los|en las)\s', detected_text.lower()):
                    continue
            
            # Si pasó todos los filtros, es probablemente una entidad legítima
            filtered_results.append(r)
                
        return filtered_results
    
    def analyze_text(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades encontradas"""
        results = self.analyzer.analyze(text=text, language=language)
        
        # Filtrar falsos positivos antes de devolver resultados
        filtered_results = self._filter_false_positives(results, text)
        
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
        filtered_results = self._filter_false_positives(results, text)
        
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text