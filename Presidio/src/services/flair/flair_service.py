from typing import List, Dict, Any, Optional
import logging
from src.utils.logger import setup_logger
from src.config.settings import FLAIR_MODEL, FLAIR_CONFIDENCE_THRESHOLD

class FlairService:
    """Servicio para validación de entidades de tipo PERSON usando Flair."""
    
    def __init__(self):
        self.logger = setup_logger("FlairService")
        self.umbral_confianza = FLAIR_CONFIDENCE_THRESHOLD
        self.tagger = None  # No cargamos el modelo al inicializar
        
    def _load_model_if_needed(self):
        """Carga el modelo Flair solo si aún no está cargado"""
        if self.tagger is None:
            try:
                self.logger.info("Cargando modelo Flair bajo demanda...")
                from flair.models import SequenceTagger
                self.tagger = SequenceTagger.load(FLAIR_MODEL)
                self.logger.info("Modelo Flair cargado correctamente")
                return True
            except Exception as e:
                self.logger.error(f"Error al cargar el modelo Flair: {str(e)}")
                return False
        return True
    
    def validate_entity(self, entity_text: str, entity_type: str) -> bool:
        """Valida si una entidad es de tipo PERSON usando Flair"""
        # Solo cargar el modelo y procesar para PERSON
        if entity_type != "PERSON":
            return False
            
        # Cargar modelo bajo demanda
        if not self._load_model_if_needed():
            return False
            
        try:
            from flair.data import Sentence
            sentence = Sentence(entity_text)
            self.tagger.predict(sentence)
            
            # Verificar si Flair detecta una entidad PER
            for entity in sentence.get_spans('ner'):
                if entity.tag == 'PER' and entity.score > self.umbral_confianza:
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error en validación Flair: {str(e)}")
            return False