from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts

class ColombianIDRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para documentos de identidad colombianos.
    
    Este reconocedor detecta diferentes tipos de documentos de identidad utilizados
    en Colombia, incluyendo:
    - Cédula de Ciudadanía (CC)
    - Tarjeta de Identidad (TI)
    - Pasaporte (PA)
    - Cédula de Extranjería (CE)
    - Registro Civil (RC)
    - NIT (para empresas)
    - Permiso Especial de Permanencia (PEP)
    """
    
    # Identificador para el reconocedor
    ENTITY = "CO_ID_NUMBER"
    
    # Patrones de documentos de identidad compilados
    DOCUMENT_PATTERNS = {
        "CC": {
            "regex": re.compile(r"(?:"
                      r"(?:(?:cedula|cédula)(?:\s+de\s+ciudadan[ií]a)?)|"
                      r"(?:c\.?\s*c\.?)|"
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:cedula|cédula|c\.?c\.?)(?:\s+(?:es|son|:))?)|"
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:cedula|cédula|c\.?c\.?))|"
                      r"(?:(?:cedula|cédula|cc|c\.c\.|c\s*c)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{7,10})", re.IGNORECASE),
            "min_digits": 7,
            "max_digits": 10,
            "allow_letters": True,
            "score": 0.9
        },
        "TI": {
            "regex": re.compile(r"(?:"
                      r"(?:(?:tarjeta)(?:\s+de\s+identidad))|"
                      r"(?:\b(?:t\.?\s*i\.?)\b)|"
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:tarjeta(?:\s+de\s+identidad)?|t\.?i\.?)(?:\s+(?:es|son|:))?)|"
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:tarjeta(?:\s+de\s+identidad)?|t\.?i\.?))|"
                      r"(?:(?:y|,)(?:\s+)(?:tarjeta(?:\s+de\s+identidad)?|t\.?i\.?))|"
                      r"(?:(?:tarjeta(?:\s+de\s+identidad)?|\bt\.?i\.?\b)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{10,11})", re.IGNORECASE),
            "min_digits": 10,
            "max_digits": 11,
            "allow_letters": True,
            "score": 0.9
        },
        "CE": {
            "regex": re.compile(r"(?:"
                      r"(?:(?:cedula|cédula)(?:\s+de\s+extranjer[ií]a)?)|"
                      r"(?:c\.?\s*e\.?)|"
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:extranjer[ií]a|c\.?e\.?)(?:\s+(?:es|son|:))?)|"
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:extranjer[ií]a|c\.?e\.?))|"
                      r"(?:(?:y|,)(?:\s+)(?:extranjer[ií]a|c\.?e\.?))|"
                      r"(?:(?:extranjeria|extranjería|ce|c\.e\.|c\s*e)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{6,8})", re.IGNORECASE),
            "pattern": r"^[A-Za-z0-9]{6,8}$",
            "score": 0.9
        },
        "NIT": {
            "regex": re.compile(r"(?:"
                      r"(?:numero\s+de\s+identificacion\s+tributaria)|"
                      r"(?:n\.?i\.?t\.?)|"
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:nit|n\.?i\.?t\.?)(?:\s+(?:es|son|:))?)|"
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:nit|n\.?i\.?t\.?))|"
                      r"(?:(?:y|,)(?:\s+)(?:nit|n\.?i\.?t\.?))|"
                      r"(?:(?:nit|n\.i\.t\.|n\s*i\s*t)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{9,10}(?:[\s-]*[A-Za-z0-9]{1})?)", re.IGNORECASE),
            "min_digits": 9,
            "max_digits": 11,
            "allow_letters": True,
            "score": 0.9
        },
        "PEP": {
            "regex": re.compile(r"(?:"
                      r"(?:permiso\s+especial\s+de\s+permanencia)|"
                      r"(?:pep)|"
                      r"(?:mi(?:\s+)(?:permiso|pep)(?:\s+es)?)|"
                      r"(?:(?:pep|permiso)(?:\s*)?(?::|=|es|es:|número|numero))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Z0-9]{5,15})", re.IGNORECASE),
            "min_length": 5,
            "max_length": 15,
            "score": 0.9
        },
        "RC": {
            "regex": re.compile(r"(?:"
                      r"(?:registro\s+(?:civil|de\s+nacimiento))|"
                      r"(?:r\.?\s*c\.?)|"
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:registro|r\.?c\.?)(?:\s+(?:es|son|:))?)|"
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:registro|r\.?c\.?))|"
                      r"(?:(?:y|,)(?:\s+)(?:registro|r\.?c\.?))|"
                      r"(?:(?:registro|rc|r\.c\.|r\s*c)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{10,11})", re.IGNORECASE),
            "min_digits": 10,
            "max_digits": 11,
            "allow_letters": True,
            "score": 0.9
        },
        "PA": {
            "regex": re.compile(r"(?:"
                      r"(?:pasaporte)|"
                      r"(?:pa\.?)|"
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:pasaporte|pa\.?)(?:\s+(?:es|son|:))?)|"
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:pasaporte|pa\.?))|"
                      r"(?:(?:y|,)(?:\s+)(?:pasaporte|pa\.?))|"
                      r"(?:(?:pasaporte|pa|p\.a\.)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{6,8})", re.IGNORECASE),
            "min_digits": 6,
            "max_digits": 8,
            "allow_letters": True,
            "score": 0.9
        }
    }
    
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = None,
        name: str = None,
    ):
        # Inicializar con valores por defecto
        if supported_entity is None:
            supported_entity = self.ENTITY
        
        if name is None:
            name = f"{self.__class__.__name__}"
        
        # Crear patrones si no se proporcionan
        if not patterns:
            patterns = []
            
            # Añadir patrones para identificación colombiana
            for doc_type, config in self.DOCUMENT_PATTERNS.items():
                patterns.append(
                    Pattern(
                        name=f"{doc_type}_pattern",
                        regex=config["regex"],
                        score=config.get("score", 0.8),
                    )
                )
        
        # Contexto para mejorar la detección
        if context is None:
            context = [
                "documento", "identidad", "identificación", "id", "número", "numero",
                "cédula", "cedula", "tarjeta", "pasaporte", "extranjería", "extranjeria",
                "registro", "civil", "nit", "tributaria", "permiso", "permanencia"
            ]
        
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )
    
    def validate_result(self, pattern_text: str) -> Tuple[bool, float]:
        """
        Valida que el texto detectado corresponda a un documento de identidad válido.
        
        Args:
            pattern_text: El texto del patrón detectado para validar
            
        Returns:
            Tupla con (es_válido, score)
        """
        # Eliminar caracteres no alfanuméricos
        clean_text = re.sub(r'[^A-Za-z0-9]', '', pattern_text)
        
        if not clean_text:
            return False, 0.0
        
        # Validaciones específicas por tipo de documento
        # Para la cédula: longitud entre 7-10 dígitos
        if len(clean_text) >= 7 and len(clean_text) <= 10 and clean_text.isdigit():
            return True, 0.95  # Probable cédula
            
        # Para TI: validar formato específico (10-11 caracteres)
        elif len(clean_text) >= 10 and len(clean_text) <= 11:
            if clean_text.isalnum():
                return True, 0.85  # Probable TI
        
        # Para CE: validar formato específico (6-8 caracteres alfanuméricos)
        elif len(clean_text) >= 6 and len(clean_text) <= 8:
            if clean_text.isalnum():
                return True, 0.85  # Probable CE
        
        # Para NIT: validar formato específico (9-10 dígitos + dígito verificación)
        elif len(clean_text) >= 9 and len(clean_text) <= 11:
            if clean_text[:-1].isdigit():
                return True, 0.9  # Probable NIT
        
        # Para PEP: validar formato (5-15 caracteres alfanuméricos)
        elif len(clean_text) >= 5 and len(clean_text) <= 15:
            if clean_text.isalnum():
                return True, 0.8  # Posible PEP
                
        return False, 0.0
    
    def analyze_using_context(
        self, text: str, entities: List[Dict[str, Any]], nlp_artifacts: NlpArtifacts
    ) -> List[Dict[str, Any]]:
        """
        Analiza el contexto para determinar si realmente es un documento de identidad.
        
        Args:
            text: El texto completo a analizar
            entities: Las entidades detectadas preliminarmente
            nlp_artifacts: Los artefactos de NLP disponibles
            
        Returns:
            Lista de entidades actualizadas con contexto
        """
        updated_entities = []
        
        for entity in entities:
            # Solo procesar si es de nuestro tipo
            if entity["entity_type"] == self.supported_entity:
                start, end = entity["start"], entity["end"]
                detected_text = text[start:end]
                
                # Buscar indicadores de contexto en el texto cercano
                # (antes o después de la entidad detectada)
                context_score = self._analyze_id_context(text, start, end)
                
                # Validar el formato del documento detectado
                is_valid, validation_score = self.validate_result(detected_text)
                
                if is_valid:
                    # Ajustar la puntuación según el contexto
                    final_score = min(0.99, (entity["score"] + context_score + validation_score) / 3)
                    entity["score"] = final_score
                    
                    # Intentar determinar el tipo de documento
                    doc_type = self._determine_document_type(detected_text, text, start, end)
                    if doc_type:
                        entity["entity_type"] = f"{self.supported_entity}_{doc_type}"
                    
                    updated_entities.append(entity)
            else:
                # Mantener otras entidades sin cambios
                updated_entities.append(entity)
                
        return updated_entities
    
    def _analyze_id_context(self, text: str, start: int, end: int) -> float:
        """
        Analiza el contexto alrededor de un número para determinar si es un ID.
        
        Args:
            text: Texto completo
            start: Posición de inicio de la entidad
            end: Posición de fin de la entidad
            
        Returns:
            Puntaje de contexto entre 0 y 1
        """
        # Tomar contexto antes y después
        context_window = 50  # caracteres
        before = text[max(0, start - context_window):start].lower()
        after = text[end:min(len(text), end + context_window)].lower()
        
        # Buscar palabras clave específicas
        context_indicators = {
            "cc": 0.3, "cédula": 0.3, "cedula": 0.3, "identidad": 0.2, 
            "identificación": 0.2, "identificacion": 0.2, "ti": 0.3, 
            "tarjeta": 0.2, "ce": 0.3, "extranjería": 0.3, "extranjeria": 0.3,
            "nit": 0.3, "registro": 0.2, "civil": 0.2, "pep": 0.3, "permanencia": 0.2
        }
        
        score = 0.0
        for word, value in context_indicators.items():
            if word in before or word in after:
                score += value
        
        return min(0.8, score)  # Limitar a un máximo de 0.8
    
    def _determine_document_type(self, detected_text: str, text: str, start: int, end: int) -> str:
        """
        Intenta determinar el tipo específico de documento de identidad.
        
        Args:
            detected_text: El texto del documento detectado
            text: El texto completo
            start: Posición de inicio de la entidad
            end: Posición de fin de la entidad
            
        Returns:
            Tipo de documento (CC, TI, CE, NIT, PEP, etc.) o cadena vacía si no se determina
        """
        # Limpiar texto detectado
        clean_text = re.sub(r'[^A-Za-z0-9]', '', detected_text)
        
        # Tomar contexto antes y después
        context_window = 50
        before = text[max(0, start - context_window):start].lower()
        after = text[end:min(len(text), end + context_window)].lower()
        
        # Buscar indicaciones explícitas del tipo de documento
        if "cedula" in before or "cédula" in before or "cc" in before:
            if "extranjeria" in before or "extranjería" in before:
                return "CE"
            return "CC"
        
        if "tarjeta" in before and "identidad" in before or "ti" in before:
            return "TI"
            
        if "registro" in before and "civil" in before or "rc" in before:
            return "RC"
            
        if "nit" in before:
            return "NIT"
            
        if "pep" in before or "permiso" in before and "permanencia" in before:
            return "PEP"
            
        if "pasaporte" in before or "pa" in before:
            return "PA"
        
        # Si no hay indicación explícita, inferir por formato
        if len(clean_text) >= 7 and len(clean_text) <= 10 and clean_text.isdigit():
            return "CC"  # Asumir cédula
            
        if len(clean_text) >= 10 and len(clean_text) <= 11:
            return "TI"  # Asumir TI
            
        if len(clean_text) >= 9 and len(clean_text) <= 11 and clean_text[:-1].isdigit():
            return "NIT"  # Asumir NIT
            
        return ""  # No se pudo determinar
    
    def analyze(
        self, text: str, entities: List[Dict[str, Any]], nlp_artifacts: NlpArtifacts
    ) -> List[Dict[str, Any]]:
        """
        Analiza el texto para detectar documentos de identidad colombianos.
        
        Args:
            text: El texto a analizar
            entities: Las entidades detectadas previamente
            nlp_artifacts: Artefactos NLP disponibles
            
        Returns:
            Lista de entidades actualizadas
        """
        # Detectar entidades usando los patrones
        pattern_entities = super().analyze(text, entities, nlp_artifacts)
        
        # Aplicar análisis contextual para mejorar la precisión
        return self.analyze_using_context(text, pattern_entities, nlp_artifacts)


def create_colombian_recognizers() -> List[ColombianIDRecognizer]:
    """
    Crea una lista de reconocedores para documentos colombianos.
    
    Returns:
        Lista de instancias de ColombianIDRecognizer
    """
    return [ColombianIDRecognizer()]