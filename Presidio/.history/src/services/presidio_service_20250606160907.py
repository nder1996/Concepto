from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import re

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Configuración de filtros
        self.min_score_threshold = {
            "DEFAULT": 0.7,        # Umbral predeterminado para cualquier entidad
            "PERSON": 0.9,         # Más estricto para nombres de personas
            "IN_PAN": 0.4,         # Más estricto para números de tarjetas
            "LOCATION": 0.9,       # Más estricto para ubicaciones
            "NRP": 0.9             # Más estricto para números de registro personal
        }
        
        # Lista de palabras técnicas y términos comunes que no deben ser anonimizados
        self.tech_terms = [
            # Frameworks y librerías
            "BootsFaces", "PrimeFaces", "Angular", "Spring", "Bootstrap", "jQuery", 
            "Jasper Reports", "Vuetify", "PrimeNG", "Vue", "React", "JSF", "Java", 
            "Spring Boot", "Spring Cloud", "JPA", "Hibernate", "MyBatis",
            "Angular Material", "Jenkins", "Docker", "Git", "Maven", "Gradle",
            "OAuth2", "JWT", "TypeScript", "HTML5", "CSS3", "Postman", "Swagger",
            "Mockito", "TestNG", "Jasmine", "Scrum", "Agile",
            
            # Conceptos técnicos
            "MVC", "API", "REST", "SOAP", "Clean Architecture", "microservicios",
            "escalables", "eficientes", "interfaces", "backend", "frontend", 
            "base de datos", "bases de datos", "responsivo", "responsive",
            "full stack", "Full Stack", "desarrollador", "Desarrollador",
            "API", "APIs", "integración", "AWS", "usabilidad", "rendimiento",
            "mantenimiento", "arquitectura", "distribuida", "normalización",
            "producción", "preventivo", "correctivo", "sistemas", "aplicaciones",
            "automatización", "Automaticé", "optimización", "transforme", 
            "expectativas", "decisiones", "requisitos", "generación", "reportes",
            "motivación", "innovación", "separación", "protección", "garantizar",
            "diseño", "usabilidad", "testing", "integrando", "desarrollo",
            "endpoints", "navegación", "accesibilidad", "plazos", "existentes",
            "optimicé", "implementé", "modernas", "robustas", "seguras",
            "Diseño Responsivo", "reutilizables", "Avanzado", "Hexagonal",
            
            # Organizaciones y términos específicos pero no sensibles
            "Profamilia", "Gencell Genética avanzada", "Ingeniero"
        ]
        
        # Construir expresiones regulares para términos técnicos
        self.tech_pattern = re.compile(r'\b(' + '|'.join(re.escape(term) for term in self.tech_terms) + r')\b', 
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