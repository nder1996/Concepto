from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any

class PresidioService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Entidades específicas a anonimizar
        self.target_entities = [
            "PERSON", 
            "PHONE_NUMBER", 
            "LOCATION", 
            "TIME", 
            "NRP", # Número de cédula/documento (Colombian ID)
            "EMAIL_ADDRESS",
            "ADDRESS"
        ]
        
        # Umbral de puntuación fijo
        self.score_threshold = 0.65
    
    def analyze_text(self, text: str, language: str = 'es') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades encontradas"""
        results = self.analyzer.analyze(text=text, language=language)
        return [{
            'entity_type': r.entity_type,
            'start': r.start,
            'end': r.end,
            'score': r.score
        } for r in results]
    
    def anonymize_text(self, text: str, language: str = 'es') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        results = self.analyzer.analyze(text=text, language=language)
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text    def anonymize_selective(self, text: str, language: str = 'es') -> str:
        """
        Anonimiza SOLO entidades específicas de Microsoft Presidio 
        basándose en un umbral de puntuación fijo.
        
        Solo se anonimizan: PERSON, PHONE, LOCATION, TIME, CEDULA, EMAIL, ADDRESS
        """
        try:
            import logging
            # Inicializar el logger
            logger = logging.getLogger(__name__)
            
            # Validar el idioma (es, en, etc.)
            supported_languages = ['es', 'en']  # Añadir más idiomas según sea necesario
            if language not in supported_languages:
                logger.warning(f"Idioma '{language}' no soportado. Usando español por defecto.")
                language = 'es'
            
            # Analizar el texto para encontrar todas las entidades
            logger.info(f"Analizando texto para anonimización selectiva (idioma: {language})")
            all_results = self.analyzer.analyze(text=text, language=language)
            
            # Log de todas las entidades encontradas para depuración
            if all_results:
                logger.info(f"Entidades encontradas: {len(all_results)}")
                for result in all_results:
                    logger.info(f"Entidad: {result.entity_type}, Score: {result.score}, Texto: {text[result.start:result.end]}")
            else:
                logger.warning("No se detectaron entidades en el texto")
                
            # Ajustar nombres de entidades: asegurarse de que los nombres coincidan exactamente
            mapping_entidades = {
                "PERSON": "PERSON",
                "PHONE_NUMBER": "PHONE_NUMBER",
                "TELEFONO": "PHONE_NUMBER",
                "CELULAR": "PHONE_NUMBER",
                "LOCATION": "LOCATION",
                "UBICACION": "LOCATION",
                "TIME": "DATE_TIME",
                "FECHA": "DATE_TIME",
                "HORA": "DATE_TIME",
                "CEDULA": "NRP",
                "CC": "NRP",
                "DOCUMENTO": "NRP",
                "EMAIL": "EMAIL_ADDRESS",
                "CORREO": "EMAIL_ADDRESS",
                "EMAIL_ADDRESS": "EMAIL_ADDRESS",
                "DIRECCION": "ADDRESS",
                "ADDRESS": "ADDRESS"
            }
            
            # Reconfigurar los tipos de entidades a filtrar
            target_entities_expanded = set()
            for entity in self.target_entities:
                target_entities_expanded.add(entity)
                # Añadir variantes del nombre si están en el mapeo
                for k, v in mapping_entidades.items():
                    if v == entity:
                        target_entities_expanded.add(k)
            
            logger.info(f"Entidades objetivo expandidas: {target_entities_expanded}")
            
            # Umbral reducido temporalmente para testing
            test_threshold = max(0.3, self.score_threshold - 0.2)  # Umbral para pruebas
            
            # Filtrar solo las entidades objetivo, primero con umbral normal
            filtered_results = [
                result for result in all_results 
                if result.entity_type in target_entities_expanded and result.score >= self.score_threshold
            ]
            
            # Si no se encuentran entidades con el umbral normal, intentar con un umbral más bajo para debug
            if not filtered_results:
                logger.warning(f"No se encontraron entidades con umbral {self.score_threshold}, probando con {test_threshold}")
                debug_results = [
                    result for result in all_results 
                    if result.entity_type in target_entities_expanded and result.score >= test_threshold
                ]
                
                if debug_results:
                    logger.warning(f"Se encontraron {len(debug_results)} entidades con umbral reducido {test_threshold}")
                    for result in debug_results:
                        logger.warning(f"Entidad potencial: {result.entity_type}, Score: {result.score}, Texto: {text[result.start:result.end]}")
            
            # Si no hay resultados que cumplan los criterios, retornar el texto original
            if not filtered_results:
                logger.warning("No hay entidades que cumplan con los criterios, retornando texto original")
                return text
            
            # Loguear las entidades que serán anonimizadas
            logger.info(f"Anonimizando {len(filtered_results)} entidades")
            for result in filtered_results:
                logger.info(f"Anonimizando: {result.entity_type}, Score: {result.score}, Texto: {text[result.start:result.end]}")
            
            # Anonimizar solo las entidades filtradas
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
              # Verificar si el texto cambió
            if anonymized.text == text:
                logger.warning("El texto no cambió después de la anonimización")
            else:
                logger.info("Anonimización exitosa")
            
            return anonymized.text
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en anonymize_selective: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return text  # En caso de error, devolver el texto original