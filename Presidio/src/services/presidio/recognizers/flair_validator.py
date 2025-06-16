from typing import List, Dict, Any, Tuple, Optional
import flair
from flair.data import Sentence
from flair.models import SequenceTagger
import re
import spacy
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)

class FlairContextValidator:
    """
    Clase para validar entidades mediante el modelo de NER de Flair.
    
    Esta clase permite utilizar modelos pre-entrenados de Flair para:
    1. Validar si una entidad detectada por Presidio es realmente una entidad del tipo esperado
    2. Proporcionar contexto adicional sobre la entidad
    3. Calcular una puntuación de confianza basada en la combinación de Presidio y Flair
    
    Ejemplo de uso:
    ```python
    validator = FlairContextValidator()
    validation_result = validator.validate_entity(
        text="Mi correo es usuario@ejemplo.com", 
        entity_text="usuario@ejemplo.com",
        entity_type="EMAIL_ADDRESS"
    )
    ```
    """
    
    # Mapeo de tipos de entidades de Presidio a tipos de entidades de Flair
    ENTITY_TYPE_MAPPING = {
        # Entidades estándar
        "PERSON": ["PER"],
        "EMAIL_ADDRESS": ["MISC"],  # No hay equivalente directo para emails
        "PHONE_NUMBER": ["MISC"],   # No hay equivalente directo para teléfonos
        "CREDIT_CARD": ["MISC"],    # No hay equivalente directo para tarjetas
        "LOCATION": ["LOC"],
        "DATE_TIME": ["MISC"],      # No hay equivalente directo para fechas
        "URL": ["MISC"],            # No hay equivalente directo para URLs
        "IP_ADDRESS": ["MISC"],     # No hay equivalente directo para IPs
        "US_SSN": ["MISC"],         # No hay equivalente directo para SSN
        "US_DRIVER_LICENSE": ["MISC"],
        
        # Entidades personalizadas
        "CO_ID_NUMBER": ["MISC"],   # No hay equivalente directo para docs colombianos
    }
    
    # Modelo por defecto de NER en español
    DEFAULT_MODEL = "flair/ner-spanish-large"
    
    def __init__(self, model_name: str = None, use_spacy: bool = True):
        """
        Inicializa el validador de contexto con un modelo de Flair.
        
        Args:
            model_name: Nombre del modelo de Flair a utilizar (por defecto: flair/ner-spanish-large)
            use_spacy: Si debe utilizarse spaCy para análisis adicional
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Inicializando FlairContextValidator")
        
        # Cargar modelo de Flair
        try:
            self.model_name = model_name or self.DEFAULT_MODEL
            self.logger.info(f"Cargando modelo Flair: {self.model_name}")
            self.model = SequenceTagger.load(self.model_name)
            self.logger.info(f"Modelo Flair cargado correctamente")
        except Exception as e:
            self.logger.error(f"Error al cargar el modelo Flair: {str(e)}")
            self.model = None
            
        # Cargar modelo spaCy si está habilitado
        self.use_spacy = use_spacy
        self.nlp = None
        if use_spacy:
            try:
                self.logger.info("Cargando modelo spaCy (es_core_news_md)")
                import spacy
                self.nlp = spacy.load("es_core_news_md")
                self.logger.info("Modelo spaCy cargado correctamente")
            except Exception as e:
                self.logger.error(f"Error al cargar el modelo spaCy: {str(e)}")
                self.use_spacy = False
    
    def validate_entity(self, 
                        text: str, 
                        entity_text: str, 
                        entity_type: str, 
                        context_window: int = 50) -> Dict[str, Any]:
        """
        Valida si una entidad detectada es realmente del tipo esperado según Flair.
        
        Args:
            text: Texto completo donde se encontró la entidad
            entity_text: El texto de la entidad detectada
            entity_type: El tipo de entidad según Presidio
            context_window: Número de caracteres alrededor de la entidad a considerar
            
        Returns:
            Dict[str, Any]: Resultado de la validación con confianza y contexto
        """
        if not self.model:
            return {"is_valid": None, "confidence": 0.0, "context": {}}
            
        # Buscar la posición de la entidad en el texto completo
        try:
            start_pos = text.index(entity_text)
            end_pos = start_pos + len(entity_text)
        except ValueError:
            self.logger.warning(f"No se encontró la entidad '{entity_text}' en el texto.")
            return {"is_valid": False, "confidence": 0.0, "context": {}}
        
        # Extraer contexto alrededor de la entidad
        context_start = max(0, start_pos - context_window)
        context_end = min(len(text), end_pos + context_window)
        context_text = text[context_start:context_end]
        
        # Ajustar la posición de la entidad en el contexto extraído
        entity_start_in_context = start_pos - context_start
        entity_end_in_context = entity_start_in_context + len(entity_text)
        
        # Crear una oración de Flair con el contexto
        sentence = Sentence(context_text)
        
        # Detectar entidades en la oración
        try:
            self.model.predict(sentence)
        except Exception as e:
            self.logger.error(f"Error al predecir con el modelo Flair: {str(e)}")
            return {"is_valid": None, "confidence": 0.0, "context": {}}
        
        # Inicializar valores predeterminados
        is_valid = False
        confidence = 0.0
        entity_info = {}
        
        # Obtener los tipos de entidades Flair equivalentes
        flair_entity_types = self.ENTITY_TYPE_MAPPING.get(entity_type, ["MISC"])
        
        # Comprobar si alguna de las entidades detectadas coincide con la entidad buscada
        for entity in sentence.get_spans('ner'):
            # Verificar si la entidad detectada se solapa con nuestra entidad
            if (entity.start_position <= entity_end_in_context and 
                entity.end_position >= entity_start_in_context):
                
                # Si el tipo de entidad coincide con alguno de los tipos esperados
                if entity.tag in flair_entity_types or "MISC" in flair_entity_types:
                    is_valid = True
                    confidence = entity.score
                    entity_info = {
                        "flair_type": entity.tag,
                        "flair_text": entity.text,
                        "flair_confidence": entity.score
                    }
                    break
        
        # Si no se encontró coincidencia directa pero es un tipo que Flair no maneja bien
        if not is_valid and "MISC" in flair_entity_types:
            # Para entidades como emails, teléfonos, etc., Flair puede no ser la mejor opción
            # En este caso, usamos validación adicional con spaCy o regex
            is_valid, confidence, additional_info = self._validate_special_entity(
                entity_text, entity_type, context_text
            )
            entity_info.update(additional_info)
        
        # Crear resultado de la validación
        validation_result = {
            "is_valid": is_valid,
            "confidence": float(confidence),
            "context": {
                "entity_info": entity_info,
                "context_text": context_text
            }
        }
        
        return validation_result
    
    def _validate_special_entity(self, 
                              entity_text: str, 
                              entity_type: str,
                              context_text: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Método auxiliar para validar entidades especiales que Flair no maneja bien.
        
        Args:
            entity_text: El texto de la entidad detectada
            entity_type: El tipo de entidad según Presidio
            context_text: El contexto alrededor de la entidad
            
        Returns:
            Tuple[bool, float, Dict[str, Any]]: Validez, confianza e información adicional
        """
        # Información adicional para devolver
        additional_info = {}
        
        # Por defecto, confiamos en la detección de Presidio para tipos especiales
        is_valid = True
        confidence = 0.7  # Confianza moderada por defecto
        
        # Validación específica según el tipo de entidad
        if entity_type == "EMAIL_ADDRESS":
            # Validar formato de email con regex
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
            if re.fullmatch(email_pattern, entity_text):
                confidence = 0.9
                additional_info["validation_method"] = "regex"
            else:
                is_valid = False
                confidence = 0.2
        
        elif entity_type == "PHONE_NUMBER":
            # Validar formato de teléfono (simplificado)
            is_valid, phone_confidence = self._validate_phone_number(entity_text)
            confidence = phone_confidence
            additional_info["validation_method"] = "regex"
            
        elif entity_type == "CO_ID_NUMBER":
            # Validar formato de documento colombiano (simplificado)
            is_valid, id_confidence = self._validate_colombian_id(entity_text)
            confidence = id_confidence
            additional_info["validation_method"] = "regex"
        
        # Usar spaCy para análisis adicional si está disponible
        if self.use_spacy and self.nlp:
            spacy_results = self._analyze_with_spacy(entity_text, context_text)
            additional_info["spacy_analysis"] = spacy_results
            
            # Ajustar confianza basada en el análisis de spaCy
            if spacy_results.get("relevant_entities"):
                confidence = min(1.0, confidence + 0.1)
        
        return is_valid, confidence, additional_info
    
    def _validate_phone_number(self, phone_text: str) -> Tuple[bool, float]:
        """
        Valida un número telefónico con expresiones regulares.
        
        Args:
            phone_text: El texto del número telefónico
            
        Returns:
            Tuple[bool, float]: Validez y nivel de confianza
        """
        # Eliminar caracteres no numéricos para la validación
        clean_phone = re.sub(r'[^\d+]', '', phone_text)
        
        # Patrones para diferentes formatos de teléfono
        patterns = [
            # Celular colombiano: 10 dígitos comenzando con 3
            (r'^3\d{9}$', 0.9),
            # Celular colombiano con prefijo país: +573 seguido de 9 dígitos
            (r'^\+?573\d{9}$', 0.9),
            # Fijo colombiano: 7-8 dígitos
            (r'^[1245678]\d{6,7}$', 0.8),
            # Internacional con prefijo
            (r'^\+\d{1,3}\d{6,12}$', 0.8),
            # Cualquier secuencia de 7-15 dígitos (menos específico)
            (r'^\d{7,15}$', 0.6)
        ]
        
        # Verificar cada patrón
        for pattern, confidence in patterns:
            if re.match(pattern, clean_phone):
                return True, confidence
        
        # Si no coincide con ningún patrón conocido
        return False, 0.2
    
    def _validate_colombian_id(self, id_text: str) -> Tuple[bool, float]:
        """
        Valida un documento de identidad colombiano con expresiones regulares.
        
        Args:
            id_text: El texto del documento
            
        Returns:
            Tuple[bool, float]: Validez y nivel de confianza
        """
        # Eliminar caracteres no numéricos para la validación
        clean_id = re.sub(r'[^\d]', '', id_text)
        
        # Si no es numérico después de la limpieza, podría ser un pasaporte
        if not clean_id.isdigit():
            # Verificar formato de pasaporte
            if re.match(r'^[A-Z0-9]{6,12}$', id_text):
                return True, 0.8
            return False, 0.1
        
        # Verificar longitud para diferentes tipos de documento
        if len(clean_id) < 6 or len(clean_id) > 12:
            return False, 0.2
        
        # Cédulas: normalmente entre 8 y 10 dígitos
        if 8 <= len(clean_id) <= 10:
            return True, 0.9
        
        # Tarjetas de identidad: normalmente 10-11 dígitos
        if 10 <= len(clean_id) <= 11:
            return True, 0.85
        
        # Cédulas de extranjería: normalmente 6-7 dígitos
        if 6 <= len(clean_id) <= 7:
            return True, 0.85
        
        # Otros formatos menos comunes
        return True, 0.7
    
    def _analyze_with_spacy(self, entity_text: str, context_text: str) -> Dict[str, Any]:
        """
        Analiza la entidad y su contexto usando spaCy para obtener información adicional.
        
        Args:
            entity_text: El texto de la entidad
            context_text: El contexto alrededor de la entidad
            
        Returns:
            Dict[str, Any]: Información adicional obtenida del análisis con spaCy
        """
        results = {}
        
        try:
            # Analizar el contexto completo
            doc = self.nlp(context_text)
            
            # Buscar entidades relevantes en el contexto
            entities = []
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
            results["entities"] = entities
            
            # Identificar entidades que podrían estar relacionadas con nuestra entidad
            relevant_entities = []
            for ent in entities:
                # Entidades que están cerca o se superponen con nuestra entidad
                if entity_text in ent["text"] or ent["text"] in entity_text:
                    relevant_entities.append(ent)
            results["relevant_entities"] = relevant_entities
            
            # Análisis de sentimiento del contexto
            results["sentiment"] = {"polarity": 0.0, "subjectivity": 0.0}  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Error en el análisis con spaCy: {str(e)}")
            results["error"] = str(e)
            
        return results
    
    def get_entity_context(self, text: str, entity_text: str, window_size: int = 100) -> Dict[str, Any]:
        """
        Extrae información contextual sobre una entidad en el texto.
        
        Args:
            text: El texto completo donde se encuentra la entidad
            entity_text: El texto de la entidad
            window_size: Tamaño de la ventana de contexto (caracteres)
            
        Returns:
            Dict[str, Any]: Información contextual sobre la entidad
        """
        try:
            # Encontrar posición de la entidad
            start_pos = text.index(entity_text)
            end_pos = start_pos + len(entity_text)
        except ValueError:
            return {"error": "Entidad no encontrada en el texto"}
        
        # Extraer contexto
        context_start = max(0, start_pos - window_size)
        context_end = min(len(text), end_pos + window_size)
        context_text = text[context_start:context_end]
        
        # Inicializar resultado
        context_info = {
            "before": text[context_start:start_pos],
            "entity": entity_text,
            "after": text[end_pos:context_end],
            "full_context": context_text
        }
        
        # Análisis adicional con spaCy si está disponible
        if self.use_spacy and self.nlp:
            try:
                # Procesar el contexto con spaCy
                doc = self.nlp(context_text)
                
                # Extraer personas mencionadas cerca
                persons = [ent.text for ent in doc.ents if ent.label_ == "PER"]
                context_info["persons"] = persons
                
                # Extraer organizaciones mencionadas cerca
                orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                context_info["organizations"] = orgs
                
                # Extraer lugares mencionados cerca
                locations = [ent.text for ent in doc.ents if ent.label_ == "LOC"]
                context_info["locations"] = locations
                
                # Palabras clave (sustantivos y adjetivos más relevantes)
                keywords = [token.text for token in doc if token.pos_ in ("NOUN", "ADJ") and token.is_alpha]
                context_info["keywords"] = keywords[:5]  # Top 5 keywords
                
            except Exception as e:
                self.logger.error(f"Error en el análisis de contexto con spaCy: {str(e)}")
        
        return context_info
