from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts
from src.config.settings import SUPPORTED_ENTITY_TYPES


class ColombianIDRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para documentos de identidad colombianos.
    
    Este reconocedor identifica los siguientes tipos de documentos:
    - Cédula de Ciudadanía (CC)
    - Tarjeta de Identidad (TI)
    - Cédula de Extranjería (CE)
    - Registro Civil (RC)
    - Pasaporte
    - NIT (Número de Identificación Tributaria)
    
    El reconocedor detecta tanto los números con prefijo (ej. "CC 1234567890")
    como los números sin prefijo, basándose en patrones y validaciones.
    """

    # Identificadores para el reconocedor
    ENTITY = "CO_ID_NUMBER" # Debe coincidir con un tipo en SUPPORTED_ENTITY_TYPES

    # Patrones para diferentes formatos de IDs colombianos
    # Con prefijos (CC, TI, CE, etc.)
    CC_PATTERN = r"\b(?:(?:c(?:(?:(?:é|e)dula)?|(?:(?:é|e)d(?:ula)?)?)|c\.?c\.?|cedula|cédula)\s*(?:de\s*ciudadan(?:í|i)a\s*)?(?:n(?:o|°|º|ú(?:mero)?)\s*)?:?\s*)?\b([1-9]\d{5,11})\b"
    TI_PATTERN = r"\b(?:(?:t(?:(?:arjeta)?|(?:arj(?:eta)?)?)|t\.?i\.?|tarjeta)\s*(?:de\s*identidad\s*)?(?:n(?:o|°|º|ú(?:mero)?)\s*)?:?\s*)?\b([1-9]\d{7,10})\b"
    CE_PATTERN = r"\b(?:(?:c(?:(?:(?:é|e)dula)?|(?:(?:é|e)d(?:ula)?)?)|c\.?e\.?|cedula|cédula)\s*(?:de\s*extranjer(?:í|i)a\s*)?(?:n(?:o|°|º|ú(?:mero)?)\s*)?:?\s*)?\b([1-9]\d{5,7})\b"
    RC_PATTERN = r"\b(?:(?:r(?:(?:egistro)?|(?:eg(?:istro)?)?)|r\.?c\.?|registro)\s*(?:civil\s*)?(?:n(?:o|°|º|ú(?:mero)?)\s*)?:?\s*)?\b([1-9]\d{7,11})\b"
    PASAPORTE_PATTERN = r"\b(?:(?:p(?:(?:asaporte)?|(?:as(?:aporte)?)?)|pasaporte|passport)\s*(?:n(?:o|°|º|ú(?:mero)?)\s*)?:?\s*)?\b([A-Z0-9]{6,12})\b"
    NIT_PATTERN = r"\b(?:(?:n(?:(?:it)?|(?:i(?:t)?)?)|n\.?i\.?t\.?|nit|número\s*de\s*identificación\s*tributaria)\s*(?:n(?:o|°|º|ú(?:mero)?)\s*)?:?\s*)?\b(\d{9,11}-\d{1}|\d{9,11})\b"

    # Sin prefijos (solo números)
    ID_NUMBER_PATTERN = r"\b(?<!\.\d*)(?<!\,\d*)(\d{7,12})(?!\.\d*)(?!\,\d*)\b"  # Entre 7 y 12 dígitos

    # Diccionario para mapear tipos de documento a sus nombres completos
    DOCUMENT_TYPES = {
        "cc": "Cédula de Ciudadanía",
        "ti": "Tarjeta de Identidad",
        "ce": "Cédula de Extranjería",
        "rc": "Registro Civil",
        "pasaporte": "Pasaporte",
        "nit": "NIT"
    }

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = None,
        name: str = None,
    ):
        """
        Inicializa el reconocedor con patrones de documentos colombianos.
        
        Args:
            patterns: Lista de patrones personalizados (opcional)
            context: Palabras de contexto para mejorar la detección
            supported_language: Idioma soportado (por defecto "es")
            supported_entity: Entidad soportada (opcional)
            name: Nombre del reconocedor (opcional)
        """
        # Definir palabras clave de contexto para mejorar la precisión
        context = context or [
            "cédula", "cedula", "documento", "identidad", "identificación", "identificacion",
            "registro", "civil", "tarjeta", "extranjería", "extranjeria", "pasaporte",
            "passport", "nit", "tributaria", "número", "numero", "document", "identity",
            "personal", "nacional", "national", "colombia", "colombiano", "colombiana",
            "documento de identidad", "número de identificación", "numero de identificacion",
            "id", "identification", "número de documento", "numero de documento"
        ]
        
        # Patrones para diferentes tipos de documentos
        patterns = [
            Pattern(name="CC Pattern", regex=self.CC_PATTERN, score=0.9),
            Pattern(name="TI Pattern", regex=self.TI_PATTERN, score=0.85),
            Pattern(name="CE Pattern", regex=self.CE_PATTERN, score=0.85),
            Pattern(name="RC Pattern", regex=self.RC_PATTERN, score=0.85),
            Pattern(name="Pasaporte Pattern", regex=self.PASAPORTE_PATTERN, score=0.8),
            Pattern(name="NIT Pattern", regex=self.NIT_PATTERN, score=0.85),
            Pattern(name="ID Number Pattern", regex=self.ID_NUMBER_PATTERN, score=0.65),
        ]
        
        # Configurar nombre y entidad
        name = name or "Colombian ID Recognizer"
        supported_entity = supported_entity or self.ENTITY
        
        # Inicializar el reconocedor base
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """
        Valida el formato y contenido de los documentos identificados.
        
        Args:
            pattern_text: El texto del patrón identificado
            
        Returns:
            bool: True si el documento es válido, False en caso contrario
        """
        # Eliminar caracteres no numéricos para documentos que deberían ser solo números
        clean_text = re.sub(r'[^\d]', '', pattern_text)
        
        # Para pasaportes (que pueden contener letras y números), devolver True directamente
        if re.match(r'[A-Z0-9]{6,12}$', pattern_text):
            return True
            
        # Para NITs con dígito de verificación
        if '-' in pattern_text:
            parts = pattern_text.split('-')
            if len(parts) == 2 and len(parts[0]) >= 9 and len(parts[1]) == 1:
                # Aquí se podría implementar la validación del dígito de verificación
                return True
        
        # Validaciones básicas para números de identificación
        if clean_text.isdigit():
            num_digits = len(clean_text)
            # Cédulas: normalmente entre 8 y 10 dígitos
            # TI: normalmente 10-11 dígitos
            # CE: normalmente 6-7 dígitos + caracteres
            # RC: normalmente 10-11 dígitos
            if 6 <= num_digits <= 12:
                # Validación básica: no empieza con cero y tiene longitud adecuada
                return clean_text[0] != '0'
        
        return False

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """
        Analiza el texto para encontrar patrones de documentos colombianos.
        
        Args:
            text: El texto a analizar
            entities: Lista de entidades a buscar
            nlp_artifacts: Artefactos NLP opcionales
            
        Returns:
            List[RecognizerResult]: Lista de resultados del reconocimiento
        """
        # Obtener resultados base del análisis de patrones
        results = super().analyze(text, entities=entities, nlp_artifacts=nlp_artifacts)
        
        # Filtrar resultados para eliminar falsos positivos
        filtered_results = []
        for result in results:
            # Extraer el texto del resultado
            start, end = result.start, result.end
            pattern_text = text[start:end]
            
            # Validar el resultado
            if self.validate_result(pattern_text):
                # Detectar el tipo de documento basado en patrones o contexto
                doc_type = self.detect_document_type(pattern_text, text, start)
                
                # Incluir el tipo de documento en los datos adicionales
                result_dict = result.to_dict()
                
                # Crear datos reconocedor
                recognizer_data = {
                    "documento_tipo": doc_type,
                    "formato_valido": True,
                    "fuente": "reconocedor_patrones"
                }
                
                # Añadir datos adicionales al resultado
                if "recognition_metadata" not in result_dict:
                    result_dict["recognition_metadata"] = {}
                
                result_dict["recognition_metadata"]["recognizer_data"] = recognizer_data
                
                # Ajustar la puntuación si hay confianza en el tipo de documento
                if doc_type != "Documento No Identificado":
                    result_dict["score"] = min(result_dict["score"] + 0.1, 1.0)
                
                # Recrear el resultado con los datos adicionales
                new_result = RecognizerResult.from_dict(result_dict)
                filtered_results.append(new_result)
        
        return filtered_results

    def detect_document_type(self, pattern_text: str, full_text: str, start_pos: int) -> str:
        """
        Detecta el tipo de documento basado en el texto identificado y su contexto.
        
        Args:
            pattern_text: El texto del patrón identificado
            full_text: El texto completo donde se encontró el patrón
            start_pos: La posición de inicio del patrón en el texto completo
            
        Returns:
            str: El tipo de documento identificado
        """
        # Buscar en el contexto cercano (hasta 20 caracteres antes)
        context_start = max(0, start_pos - 20)
        context_text = full_text[context_start:start_pos].lower()
        
        # Verificar prefijos comunes en el contexto
        if re.search(r'(^|\s)(c(\.|é|e)d(ula)?(\s+de\s+ciudadan(í|i)a)?|c\.?c\.?)\b', context_text):
            return self.DOCUMENT_TYPES["cc"]
        elif re.search(r'(^|\s)(t(arj(eta)?)?(\s+de\s+identidad)?|t\.?i\.?)\b', context_text):
            return self.DOCUMENT_TYPES["ti"]
        elif re.search(r'(^|\s)(c(\.|é|e)d(ula)?(\s+de\s+extranjer(í|i)a)?|c\.?e\.?)\b', context_text):
            return self.DOCUMENT_TYPES["ce"]
        elif re.search(r'(^|\s)(r(eg(istro)?)?(\s+civil)?|r\.?c\.?)\b', context_text):
            return self.DOCUMENT_TYPES["rc"]
        elif re.search(r'(^|\s)(p(as(aporte)?)?|pasaporte|passport)\b', context_text):
            return self.DOCUMENT_TYPES["pasaporte"]
        elif re.search(r'(^|\s)(n(i(t)?)?|n\.?i\.?t\.?)\b', context_text):
            return self.DOCUMENT_TYPES["nit"]
        
        # Si no se encontró un prefijo específico, intentar determinar por el formato
        # Verificar si el formato es de un NIT (con guión)
        if '-' in pattern_text or re.match(r'\d{9,11}-\d{1}', pattern_text):
            return self.DOCUMENT_TYPES["nit"]
        
        # Para pasaportes (combinación de letras y números)
        if re.match(r'[A-Z0-9]{6,12}$', pattern_text):
            return self.DOCUMENT_TYPES["pasaporte"]
        
        # Para el resto, verificar por longitud (heurística simple)
        digits = re.sub(r'[^\d]', '', pattern_text)
        length = len(digits)
        
        if length >= 8 and length <= 10:  # Cédulas normalmente tienen entre 8 y 10 dígitos
            return self.DOCUMENT_TYPES["cc"]
        elif length >= 10 and length <= 11:  # TI normalmente tiene 10-11 dígitos
            if int(digits) < 1100000000:  # Las TI suelen ser menores que este valor
                return self.DOCUMENT_TYPES["ti"]
            else:
                return self.DOCUMENT_TYPES["cc"]
        elif length >= 6 and length <= 7:  # CE normalmente tiene 6-7 dígitos
            return self.DOCUMENT_TYPES["ce"]
        
        # Si no se pudo determinar, devolver un valor genérico
        return "Documento No Identificado"

    def enhance_results_with_nlp(self, results: List[RecognizerResult], 
                               nlp_artifacts: NlpArtifacts, 
                               text: str) -> List[RecognizerResult]:
        """
        Mejora los resultados utilizando análisis de lenguaje natural.
        
        Args:
            results: Resultados del reconocedor
            nlp_artifacts: Artefactos NLP
            text: El texto completo analizado
            
        Returns:
            List[RecognizerResult]: Resultados mejorados
        """
        enhanced_results = []
        
        # Extraer entidades conocidas del análisis NLP
        entities = nlp_artifacts.entities if nlp_artifacts and hasattr(nlp_artifacts, 'entities') else []
        
        # Diccionario para mapear entidades detectadas con sus posiciones
        entity_positions = {}
        for ent in entities:
            entity_text = ent.text
            entity_label = ent.label_
            entity_start = ent.start
            entity_end = ent.end
            
            # Almacenar la entidad con su tipo y posición
            entity_positions[(entity_start, entity_end)] = (entity_text, entity_label)
        
        for result in results:
            # Verificar si el resultado coincide con alguna entidad de NLP
            result_start, result_end = result.start, result.end
            result_dict = result.to_dict()
            
            # Inicializar datos del reconocedor si no existen
            if "recognition_metadata" not in result_dict:
                result_dict["recognition_metadata"] = {}
            if "recognizer_data" not in result_dict["recognition_metadata"]:
                result_dict["recognition_metadata"]["recognizer_data"] = {}
            
            # Verificar si hay alguna entidad NLP que se solape con nuestro resultado
            for (ent_start, ent_end), (ent_text, ent_label) in entity_positions.items():
                # Verificar solapamiento
                if (result_start <= ent_end and result_end >= ent_start):
                    # Verificar si la entidad es relevante para documentos
                    if ent_label in ["PER", "ORG", "ID", "DOC"]:
                        # Añadir información de la entidad NLP a los datos del reconocedor
                        result_dict["recognition_metadata"]["recognizer_data"]["nlp_entity"] = {
                            "tipo": ent_label,
                            "texto": ent_text,
                            "confianza": "alta" if ent_label in ["ID", "DOC"] else "media"
                        }
                        
                        # Ajustar la puntuación basada en la entidad NLP
                        if ent_label in ["ID", "DOC"]:
                            result_dict["score"] = min(result_dict["score"] + 0.15, 1.0)
                        else:
                            result_dict["score"] = min(result_dict["score"] + 0.05, 1.0)
                        
                        break
            
            # Recrear el resultado con los datos mejorados
            enhanced_result = RecognizerResult.from_dict(result_dict)
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
