from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts
from src.config.settings import SUPPORTED_ENTITY_TYPES

# Importamos la clase ColombianIDRecognizer
from .recognizer_co_identity_number import ColombianIDRecognizer


class PhoneRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para números telefónicos colombianos e internacionales.
    
    Este reconocedor identifica los siguientes formatos:
    - Números celulares colombianos (10 dígitos, prefijo 3)
    - Números fijos colombianos (7-8 dígitos con prefijo de ciudad)
    - Números internacionales (con prefijo de país, ej. +1, +44)
    - Números con formato (código de área) número
    
    El reconocedor es capaz de identificar números en diferentes formatos
    de escritura y con diversos separadores.
    """
    
    # Identificadores para el reconocedor
    ENTITY = "PHONE_NUMBER" # Debe coincidir con un tipo en SUPPORTED_ENTITY_TYPES
    
    # Patrones para diferentes formatos de teléfonos
    # Celulares colombianos: 10 dígitos comenzando con 3
    CO_MOBILE_PATTERN = r"(?<!\+57)(?<!\d)(?:\+?57)?[\s\-\.]?3\d{2}[\s\-\.]?\d{3}[\s\-\.]?\d{4}(?!\d)"
    
    # Números fijos: 7-8 dígitos, posiblemente con código de ciudad (1, 2, 4, 5, 6, 7, 8)
    CO_LANDLINE_PATTERN = r"(?<!\d)(?:\+?57[\s\-\.]?)?(?:1|2|4|5|6|7|8)[\s\-\.]?(?:\d[\s\-\.]?){6,7}(?!\d)"
    
    # Números internacionales: prefijo de país diferente a Colombia
    INTL_PHONE_PATTERN = r"(?<!\d)\+(?!57)(?:\d{1,3})[\s\-\.]?(?:\d[\s\-\.]?){6,14}(?!\d)"
    
    # Formato con paréntesis: (código) número
    PARENTHESIS_PATTERN = r"\((?:\+?57|3\d{2}|\d{1,3})\)[\s\-\.]?(?:\d[\s\-\.]?){6,14}(?!\d)"
    
    # WhatsApp estilo: wa.me/+número
    WHATSAPP_PATTERN = r"wa\.me\/\+?(?:\d[\s\-\.]?){6,15}(?!\d)"
    
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = None,
        name: str = None,
    ):
        """
        Inicializa el reconocedor con patrones para números telefónicos.
        
        Args:
            patterns: Lista de patrones personalizados (opcional)
            context: Palabras de contexto para mejorar la detección
            supported_language: Idioma soportado (por defecto "es")
            supported_entity: Entidad soportada (opcional)
            name: Nombre del reconocedor (opcional)
        """
        # Definir palabras clave de contexto para mejorar la precisión
        context = context or [
            "teléfono", "telefono", "celular", "móvil", "movil",
            "número", "numero", "contacto", "llamar", "marcar",
            "phone", "mobile", "cell", "contact", "whatsapp",
            "tel", "tel.", "tel:", "tels", "tels.", "tels:",
            "teléfonos", "telefonos", "números", "numeros",
            "línea", "linea", "fijo", "extensión", "extension",
            "ext", "ext.", "ext:", "líneas", "lineas",
            "comunicarse", "comuníquese", "comuniquese",
        ]
        
        # Patrones para diferentes tipos de números telefónicos
        patterns = [
            Pattern(name="CO Mobile Pattern", regex=self.CO_MOBILE_PATTERN, score=0.9),
            Pattern(name="CO Landline Pattern", regex=self.CO_LANDLINE_PATTERN, score=0.85),
            Pattern(name="International Phone Pattern", regex=self.INTL_PHONE_PATTERN, score=0.85),
            Pattern(name="Parenthesis Pattern", regex=self.PARENTHESIS_PATTERN, score=0.85),
            Pattern(name="WhatsApp Pattern", regex=self.WHATSAPP_PATTERN, score=0.9),
        ]
        
        # Configurar nombre y entidad
        name = name or "Phone Number Recognizer"
        supported_entity = supported_entity or self.ENTITY
        
        # Inicializar el reconocedor base
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )
        
        # Crear instancia de ColombianIDRecognizer para ayudar en la validación
        self.co_id_recognizer = ColombianIDRecognizer()
    
    def validate_result(self, pattern_text: str) -> bool:
        """
        Valida el formato y contenido de los números telefónicos identificados.
        
        Args:
            pattern_text: El texto del patrón identificado
            
        Returns:
            bool: True si el número telefónico es válido, False en caso contrario
        """
        # Eliminar caracteres no numéricos excepto el '+'
        clean_text = re.sub(r'[^\d+]', '', pattern_text)
        
        # Quitar cualquier prefijo + y validar que solo tenga dígitos
        if clean_text.startswith('+'):
            clean_text = clean_text[1:]
        
        # Validar que lo que queda sean solo dígitos
        if not clean_text.isdigit():
            return False
        
        # Validar la longitud del número (mínimo 7 dígitos, máximo 15)
        if len(clean_text) < 7 or len(clean_text) > 15:
            return False
        
        # Para celulares colombianos específicamente
        if len(clean_text) == 10 and clean_text.startswith('3'):
            # Celular colombiano: debe comenzar con 3 y tener 10 dígitos
            return True
        
        # Para números colombianos con prefijo de país
        if len(clean_text) == 12 and clean_text.startswith('573'):
            # Celular colombiano con prefijo: debe comenzar con 573 y tener 12 dígitos
            return True
        
        # Para números fijos colombianos
        if 7 <= len(clean_text) <= 8 and clean_text[0] in ['1', '2', '4', '5', '6', '7', '8']:
            # Número fijo: debe comenzar con uno de esos dígitos y tener 7-8 dígitos
            return True
        
        # Para números fijos colombianos con prefijo de país
        if len(clean_text) == 9 or len(clean_text) == 10:
            if clean_text.startswith('571') or clean_text.startswith('572'):
                return True
        
        # Para números internacionales
        if len(clean_text) >= 8 and len(clean_text) <= 15:
            # Aceptar como número internacional (más genérico)
            return True
        
        # Si llegamos aquí, el formato no es válido
        return False

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """
        Analiza el texto para encontrar patrones de números telefónicos.
        
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
                # Detectar el tipo de teléfono basado en patrones
                phone_type, country_code = self.detect_phone_type(pattern_text)
                
                # Incluir el tipo de teléfono en los datos adicionales
                result_dict = result.to_dict()
                
                # Crear datos reconocedor
                recognizer_data = {
                    "telefono_tipo": phone_type,
                    "codigo_pais": country_code,
                    "formato_valido": True,
                    "fuente": "reconocedor_patrones"
                }
                
                # Añadir datos adicionales al resultado
                if "recognition_metadata" not in result_dict:
                    result_dict["recognition_metadata"] = {}
                
                result_dict["recognition_metadata"]["recognizer_data"] = recognizer_data
                
                # Ajustar la puntuación basada en el tipo de teléfono
                if phone_type == "Celular Colombia" or phone_type == "Fijo Colombia":
                    result_dict["score"] = min(result_dict["score"] + 0.05, 1.0)
                
                # Verificar que no sea un documento de identidad (para evitar falsos positivos)
                id_results = self.co_id_recognizer.analyze(
                    pattern_text, [self.co_id_recognizer.ENTITY], nlp_artifacts
                )
                
                # Si el texto se reconoce como documento de identidad con alta confianza,
                # reducir nuestra confianza como teléfono
                if id_results and id_results[0].score > 0.8:
                    result_dict["score"] = max(result_dict["score"] - 0.3, 0.1)
                
                # Recrear el resultado con los datos adicionales
                new_result = RecognizerResult.from_dict(result_dict)
                filtered_results.append(new_result)
        
        return filtered_results

    def detect_phone_type(self, pattern_text: str) -> Tuple[str, str]:
        """
        Detecta el tipo de teléfono basado en el patrón identificado.
        
        Args:
            pattern_text: El texto del patrón identificado
            
        Returns:
            Tuple[str, str]: Tipo de teléfono y código de país
        """
        # Eliminar caracteres no numéricos excepto '+'
        clean_text = re.sub(r'[^\d+]', '', pattern_text)
        
        country_code = ""
        phone_type = "Número Internacional"
        
        # Detectar el código de país si existe
        if clean_text.startswith('+'):
            if clean_text.startswith('+57'):
                country_code = "+57"
                # Quitar el código de país para analizar el resto
                clean_text = clean_text[3:]
            else:
                # Tomar los primeros dígitos después del + como código de país
                match = re.match(r'\+(\d{1,3})', clean_text)
                if match:
                    country_code = "+" + match.group(1)
                    # Suponemos que es un número internacional
                    return "Número Internacional", country_code
        
        # Sin el '+' explícito, verificar si comienza con 57
        if not country_code and clean_text.startswith('57'):
            country_code = "+57"
            clean_text = clean_text[2:]
        
        # Para identificar el tipo específico de número colombiano
        if country_code == "+57" or not country_code:
            # Celular colombiano: comienza con 3 y tiene 10 dígitos
            if clean_text.startswith('3') and (len(clean_text) == 10 or len(clean_text) == 9):
                phone_type = "Celular Colombia"
            # Fijo colombiano: comienza con 1,2,4,5,6,7,8 y tiene 7-8 dígitos
            elif clean_text[0] in ['1', '2', '4', '5', '6', '7', '8'] and (7 <= len(clean_text) <= 8):
                phone_type = "Fijo Colombia"
        
        # Si no se identificó un código de país pero es un número colombiano
        if not country_code and (phone_type == "Celular Colombia" or phone_type == "Fijo Colombia"):
            country_code = "+57"
        
        return phone_type, country_code if country_code else "Desconocido"

    def enhance_results_with_context(self, results: List[RecognizerResult], 
                                   text: str) -> List[RecognizerResult]:
        """
        Mejora los resultados utilizando el contexto del texto.
        
        Args:
            results: Resultados del reconocedor
            text: El texto completo analizado
            
        Returns:
            List[RecognizerResult]: Resultados mejorados con información de contexto
        """
        enhanced_results = []
        
        # Palabras clave que pueden indicar el propósito del número
        purpose_keywords = {
            "whatsapp": "WhatsApp",
            "ws": "WhatsApp",
            "wsp": "WhatsApp",
            "wa.me": "WhatsApp",
            "móvil": "Celular",
            "movil": "Celular",
            "celular": "Celular",
            "cell": "Celular",
            "fijo": "Fijo",
            "casa": "Fijo",
            "oficina": "Trabajo",
            "trabajo": "Trabajo",
            "laboral": "Trabajo",
            "empresa": "Trabajo",
            "corporativo": "Trabajo",
            "business": "Trabajo",
            "personal": "Personal",
            "contacto": "Contacto",
            "emergencia": "Emergencia",
            "urgencia": "Emergencia"
        }
        
        for result in results:
            # Extraer el texto del resultado
            start, end = result.start, result.end
            result_dict = result.to_dict()
            
            # Inicializar datos del reconocedor si no existen
            if "recognition_metadata" not in result_dict:
                result_dict["recognition_metadata"] = {}
            if "recognizer_data" not in result_dict["recognition_metadata"]:
                result_dict["recognition_metadata"]["recognizer_data"] = {}
            
            # Buscar en el contexto cercano (hasta 30 caracteres antes y después)
            context_start = max(0, start - 30)
            context_end = min(len(text), end + 30)
            context_text = text[context_start:context_end].lower()
            
            # Buscar palabras clave de propósito
            purpose = None
            for keyword, purpose_value in purpose_keywords.items():
                if keyword.lower() in context_text:
                    purpose = purpose_value
                    break
            
            # Añadir información de propósito si se encontró
            if purpose:
                result_dict["recognition_metadata"]["recognizer_data"]["proposito"] = purpose
            
            # Recrear el resultado con los datos mejorados
            enhanced_result = RecognizerResult.from_dict(result_dict)
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
