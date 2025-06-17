from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any, Set
import re
import logging
from src.utils.exclusion_manager import ExclusionManager

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Inicializar el gestor de exclusiones
        self.exclusion_manager = ExclusionManager()
          # Obtener las configuraciones del gestor de exclusiones
        self.min_score_threshold = self.exclusion_manager.confidence_thresholds
        self.safe_terms_by_type = self.exclusion_manager.safe_terms_by_type
        self.tech_pattern = self.exclusion_manager.tech_pattern
        self.regex_filters = self.exclusion_manager.regex_filters
    
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
                  # 2. Verificar si es una palabra técnica general (para cualquier tipo)
            if self.tech_pattern and self.tech_pattern.search(detected_text):
                continue
                
            # 3. Verificar si es un término seguro específico para el tipo de entidad
            entity_safe_terms = self.safe_terms_by_type.get(entity_type, set())
            if detected_text in entity_safe_terms:
                continue
                
            # 4. Reglas específicas por tipo de entidad usando expresiones regulares
            if entity_type in self.regex_filters:
                pattern = self.regex_filters[entity_type]
                
                # Aplicar regla según el tipo de entidad
                if entity_type == "IN_PAN":
                    # Para números PAN, filtrar si NO tiene el formato válido (debe tener suficientes dígitos)
                    if not re.search(pattern, detected_text):
                        continue
                        
                elif entity_type == "PERSON":
                    # Para personas, filtrar si NO parece un nombre completo típico
                    if not re.search(pattern, detected_text):
                        # Si es una frase larga o no tiene formato de nombre, es probable que sea un falso positivo
                        if len(detected_text.split()) > 2 or " de " in detected_text.lower():
                            continue
                            
                elif entity_type == "LOCATION":
                    # Para ubicaciones, filtrar SI coincide con patrones comunes incorrectos
                    if re.match(pattern, detected_text.lower()):
                        continue
            
            # 5. Reglas adicionales por contexto
            
            # Para correos electrónicos, verificar dominio corporativo/educativo
            if entity_type == "EMAIL_ADDRESS" and "@" in detected_text:
                domain = detected_text.split("@")[1].lower()
                if domain in ["example.com", "test.com", "empresa.com", "company.com"]:
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
            'score': r.score        } for r in filtered_results]
    
    def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        results = self.analyzer.analyze(text=text, language=language)
        
        # Filtrar falsos positivos antes de anonimizar
        filtered_results = self._filter_false_positives(results, text)
        
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text
    
    def add_tech_term(self, term: str) -> None:
        """
        Añade un término técnico a la lista de exclusión
        
        Args:
            term: Término técnico a añadir
        """
        self.exclusion_manager.add_tech_term(term)
        # Actualizar la referencia local
        self.tech_pattern = self.exclusion_manager.tech_pattern
    
    def add_safe_term_for_entity(self, term: str, entity_type: str) -> None:
        """
        Añade un término seguro para un tipo específico de entidad
        
        Args:
            term: Término a añadir
            entity_type: Tipo de entidad (PERSON, LOCATION, etc.)
        """
        self.exclusion_manager.add_safe_term_for_entity(term, entity_type)
    
    def export_exclusion_lists(self, filename: str = None) -> bool:
        """
        Exporta las listas de exclusión a un archivo
        
        Args:
            filename: Ruta del archivo para guardar la configuración
            
        Returns:
            True si la exportación fue exitosa
        """
        if filename is None:
            filename = "exclusion_lists_export.py"
        return self.exclusion_manager.export_to_file(filename)