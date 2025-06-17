# filepath: c:\Users\AndersonArévalo\Documents\MicrosftPresidio\ModularPresidio_original_1\src\services\presidio_service.py
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PresidioService:
    def __init__(self):
        # Inicializar el analizador y anonimizador de Presidio
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Diccionario con entidades y sus umbrales de confianza predeterminados
        self.entities_thresholds = {
            "PERSON": 0.6,           # Nombres de personas
            "PHONE_NUMBER": 0.7,     # Teléfonos
            "LOCATION": 0.6,         # Ubicaciones
            "DATE_TIME": 0.6,        # Referencias de tiempo
            "NRP": 0.8,              # Cédula/documento de identidad
            "EMAIL_ADDRESS": 0.8,    # Correos electrónicos
            "ADDRESS": 0.65          # Direcciones
        }
    
    def analyze_text(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades encontradas"""
        try:
            results = self.analyzer.analyze(text=text, language=language)
            return [{
                'entity_type': r.entity_type,
                'start': r.start,
                'end': r.end,
                'score': r.score
            } for r in results]
        except Exception as e:
            logger.error(f"Error al analizar texto: {str(e)}")
            return []
    
    def anonymize_text(self, text: str, language: str = 'en') -> str:
        """Anonimiza texto reemplazando entidades sensibles"""
        try:
            results = self.analyzer.analyze(text=text, language=language)
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized.text
        except Exception as e:
            logger.error(f"Error al anonimizar texto: {str(e)}")
            return text
    
    def anonymize_specific_entities(self, text: str, language: str = 'en', 
                                   custom_thresholds: Dict[str, float] = None) -> str:
        """
        Anonimiza solo entidades específicas con umbrales de confianza predeterminados para cada tipo:
        - PERSON (nombres de personas): 0.6
        - PHONE_NUMBER (números telefónicos): 0.7
        - LOCATION (ubicaciones): 0.6
        - DATE_TIME (referencias de tiempo): 0.6
        - NRP (cédula/documento de identidad): 0.8
        - EMAIL_ADDRESS (correos electrónicos): 0.8
        - ADDRESS (direcciones): 0.65
        """
        try:
            # Configuración de registro para diagnóstico
            logger.info(f"Iniciando anonimización específica: texto de {len(text)} caracteres, idioma: {language}")
            
            # Forzar modelo en español si es necesario
            if language == 'es':
                try:
                    import spacy
                    # Verificar si tenemos el modelo español
                    if spacy.util.is_package("es_core_news_md"):
                        nlp = spacy.load("es_core_news_md")
                        logger.info("Usando modelo español para análisis")
                except Exception as e:
                    logger.error(f"Error cargando modelo español: {str(e)}")
            
            # Usar umbrales personalizados si se proporcionan, de lo contrario usar los predeterminados
            thresholds = self.entities_thresholds.copy()
            if custom_thresholds:
                thresholds.update(custom_thresholds)
                logger.info(f"Umbrales personalizados: {custom_thresholds}")
            
            # Analizar el texto para encontrar todas las entidades
            all_results = self.analyzer.analyze(text=text, language=language)
            logger.info(f"Entidades encontradas: {len(all_results)}")
            
            # Registrar todas las entidades encontradas para diagnóstico
            for result in all_results:
                entity_text = text[result.start:result.end]
                logger.info(f"Entidad: {result.entity_type}, Score: {result.score}, Texto: {entity_text}")
            
            # Si hay error con los reconocedores, prueba con inglés
            if not all_results and language != 'en':
                logger.warning("No se encontraron entidades en español, probando con inglés")
                all_results = self.analyzer.analyze(text=text, language='en')
                language = 'en'  # Cambiar a inglés para el resto del proceso
            
            # Filtrar solo las entidades que queremos anonimizar y que superen su umbral específico
            filtered_results = []
            for r in all_results:
                if r.entity_type in thresholds and r.score >= thresholds[r.entity_type]:
                    filtered_results.append(r)
                    logger.info(f"Entidad aceptada: {r.entity_type}, Score: {r.score}")
                elif r.entity_type in thresholds:
                    logger.info(f"Entidad rechazada por puntaje: {r.entity_type}, Score: {r.score} < {thresholds[r.entity_type]}")
            
            logger.info(f"Entidades filtradas: {len(filtered_results)} de {len(all_results)}")
            
            # Anonimizar solo las entidades filtradas
            if filtered_results:
                try:
                    anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
                    logger.info("Anonimización completada correctamente")
                    return anonymized.text
                except Exception as e:
                    logger.error(f"Error al anonimizar texto con entidades filtradas: {str(e)}")
                    return text
            else:
                logger.warning("No hay entidades para anonimizar después del filtrado")
                return text
                
        except Exception as e:
            logger.error(f"Error en anonymize_specific_entities: {str(e)}")
            return text
