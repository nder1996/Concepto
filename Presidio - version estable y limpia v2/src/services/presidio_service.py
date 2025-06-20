from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import logging
from src.config.entity_config import TARGET_ENTITIES, THRESHOLDS_BY_LANGUAGE
from src.config.language_config import initialize_language_analyzers, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from src.utils.logger import setup_logger

class PresidioService:
    def __init__(self):
        self.logger = setup_logger(__name__)
        
        # Inicializar analizadores
        try:
            self.analyzers = initialize_language_analyzers()
            self.anonymizer = AnonymizerEngine()
        except Exception as e:
            self.logger.error(f"Error al inicializar: {str(e)}")
            raise
        
        # Configuración
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        self.target_entities = TARGET_ENTITIES
        self.thresholds_by_language = THRESHOLDS_BY_LANGUAGE
    
    def analyze_text(self, text: str, language: str = 'es') -> List[Dict[str, Any]]:
        """Analiza texto y retorna entidades detectadas que superan el umbral"""
        # Seleccionar analizador y umbrales
        analyzer = self.analyzers.get(language, self.analyzers[self.default_language])
        thresholds = self.thresholds_by_language.get(language, self.thresholds_by_language['en'])
        
        raw_results = analyzer.analyze(text=text, entities=self.target_entities, language=language)
        filtered_results = [
            r for r in raw_results
            if self._is_valid_entity(r.entity_type, r.score, thresholds)
        ]
        
        # Log detallado de entidades detectadas
        self._log_entity_analysis(text, raw_results, thresholds, operation="ANÁLISIS")
        
        # Retornar solo las entidades válidas como dicts
        return [
            {
                'entity_type': r.entity_type,
                'start': r.start,
                'end': r.end,
                'score': r.score
            }
            for r in filtered_results
        ]
    
    def anonymize_text(self, text: str, language: str = 'es') -> str:
        """Anonimiza texto reemplazando entidades específicas"""
        # Validar idioma
        if language not in self.supported_languages:
            language = self.default_language
        
        # Seleccionar analizador y umbrales
        analyzer = self.analyzers.get(language, self.analyzers[self.default_language])
        thresholds = self.thresholds_by_language.get(language, self.thresholds_by_language['en'])
        
        raw_results = analyzer.analyze(text=text, entities=self.target_entities, language=language)
        filtered_results = [
            r for r in raw_results
            if self._is_valid_entity(r.entity_type, r.score, thresholds)
        ]
        
        # Log detallado de entidades detectadas para anonimización
        self._log_entity_analysis(text, raw_results, thresholds, operation="ANONIMIZACIÓN")
        
        # Anonimizar solo entidades válidas
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=filtered_results)
        return anonymized.text
    
    def _log_entity_analysis(self, text: str, results, thresholds: dict, operation: str):
        """Logger especializado para análisis de entidades"""
        if not results:
            self.logger.info(f"🔍 {operation} - No se detectaron entidades")
            return
        
        self.logger.info(f"🔍 === {operation} DE ENTIDADES ===")
        self.logger.info(f"📝 Texto: {len(text)} caracteres")
        self.logger.info(f"🎯 Total detectadas: {len(results)}")
        
        accepted = []
        rejected = []
        
        for r in results:
            entity_text = text[r.start:r.end]
            threshold = thresholds.get(r.entity_type, 0.80)
            is_target = r.entity_type in self.target_entities
            score_ok = r.score >= threshold
            is_valid = is_target and score_ok
            
            entity_info = {
                'type': r.entity_type,
                'text': entity_text,
                'score': round(r.score, 3),
                'threshold': threshold,
                'start': r.start,
                'end': r.end
            }
            
            if is_valid:
                accepted.append(entity_info)
            else:
                rejected.append(entity_info)
        
        # Log entidades aceptadas
        if accepted:
            self.logger.info(f"✅ ENTIDADES ACEPTADAS ({len(accepted)}):")
            for entity in accepted:
                self.logger.info(
                    f"   ➤ {entity['type']}: '{entity['text']}' "
                    f"(Score: {entity['score']} ≥ {entity['threshold']}) "
                    f"[{entity['start']}:{entity['end']}]"
                )
        
        # Log entidades rechazadas
        if rejected:
            self.logger.info(f"❌ ENTIDADES RECHAZADAS ({len(rejected)}):")
            for entity in rejected:
                is_target = entity['type'] in self.target_entities
                reason = "Score bajo" if is_target else "No es entidad objetivo"
                self.logger.info(
                    f"   ➤ {entity['type']}: '{entity['text']}' "
                    f"(Score: {entity['score']} vs {entity['threshold']}) "
                    f"- {reason}"
                )
        
        self.logger.info(f"📊 Resumen: {len(accepted)} aceptadas, {len(rejected)} rechazadas")
        self.logger.info("=" * 60)
    
    def _is_valid_entity(self, entity_type: str, score: float, thresholds: dict) -> bool:
        """Verifica si una entidad es válida para procesar"""
        return (
            entity_type in self.target_entities and 
            score >= thresholds.get(entity_type, 0.80)
        )