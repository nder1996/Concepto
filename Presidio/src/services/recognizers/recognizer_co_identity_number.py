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
    - Visa colombiana
    
    Los documentos pueden contener tanto números como letras, permitiendo formatos como:
    - C.C. 2333I344 (combinación de números y letras)
    
    También es capaz de detectar documentos en contextos complejos como:
    - "Mi cédula es 30293834 y pasaporte 394848"
    - "Tengo tarjeta de identidad 1234567890 y registro civil 9876543210"
    - Frases con múltiples documentos mencionados en secuencia
    """
    
    # Identificador para el reconocedor
    ENTITY = "CO_ID_NUMBER"
      # Patrones de documentos de identidad compilados para mayor eficiencia
    DOCUMENT_PATTERNS = {        "CC": {
            "regex": re.compile(r"(?:"
                      # Cédula de ciudadanía con variantes completas
                      r"(?:(?:cedula|cédula)(?:\s+de\s+ciudadan[ií]a)?)|"
                      # Abreviaturas con puntos o sin puntos y espacios opcionales
                      r"(?:c\.?\s*c\.?)|"
                      # Términos posesivos - ampliados para incluir más contextos
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:cedula|cédula|c\.?c\.?)(?:\s+(?:es|son|:))?)|"
                      # Contextos de tipo "tengo cédula", "con cédula", etc.
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:cedula|cédula|c\.?c\.?))|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:cedula|cédula|cc|c\.c\.|c\s*c)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{7,10})", re.IGNORECASE),
            "min_digits": 7,
            "max_digits": 10,
            "allow_letters": True,
            "score": 0.9
        },        "TI": {
            "regex": re.compile(r"(?:"
                      # Tarjeta de identidad con variantes completas - más restrictivo
                      r"(?:(?:tarjeta)(?:\s+de\s+identidad))|"
                      # Abreviaturas con puntos o sin puntos - asegurarse que sean aisladas
                      r"(?:\b(?:t\.?\s*i\.?)\b)|"
                      # Términos posesivos - más restrictivos
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:tarjeta(?:\s+de\s+identidad)?|t\.?i\.?)(?:\s+(?:es|son|:))?)|"
                      # Contextos de tipo "tengo tarjeta", "con tarjeta", etc.
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:tarjeta(?:\s+de\s+identidad)?|t\.?i\.?))|"
                      # Para capturar escenarios como "mi cédula es X y tarjeta Y"
                      r"(?:(?:y|,)(?:\s+)(?:tarjeta(?:\s+de\s+identidad)?|t\.?i\.?))|"
                      # Expresiones con dos puntos o igual - más restrictivas
                      r"(?:(?:tarjeta(?:\s+de\s+identidad)?|\bt\.?i\.?\b)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{10,11})", re.IGNORECASE),
            "min_digits": 10,
            "max_digits": 11,
            "allow_letters": True,
            "score": 0.9
        },        "CE": {
            "regex": re.compile(r"(?:"
                      # Cédula de extranjería con variantes completas
                      r"(?:(?:cedula|cédula)(?:\s+de\s+extranjer[ií]a)?)|"
                      # Abreviaturas con puntos o sin puntos
                      r"(?:c\.?\s*e\.?)|"
                      # Términos posesivos - ampliados para incluir más contextos
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:extranjer[ií]a|c\.?e\.?)(?:\s+(?:es|son|:))?)|"
                      # Contextos de tipo "tengo cédula de extranjería", etc.
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:extranjer[ií]a|c\.?e\.?))|"
                      # Para capturar escenarios como "mi cédula es X y extranjería Y"
                      r"(?:(?:y|,)(?:\s+)(?:extranjer[ií]a|c\.?e\.?))|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:extranjeria|extranjería|ce|c\.e\.|c\s*e)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{6,8})", re.IGNORECASE),
            "min_digits": 6,
            "max_digits": 8,
            "allow_letters": True,
            "score": 0.9
        },        "RC": {
            "regex": re.compile(r"(?:"
                      # Registro civil con variantes completas
                      r"(?:registro\s+(?:civil|de\s+nacimiento))|"
                      # Abreviaturas con puntos o sin puntos
                      r"(?:r\.?\s*c\.?)|"
                      # Términos posesivos - ampliados para incluir más contextos
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:registro|r\.?c\.?)(?:\s+(?:es|son|:))?)|"
                      # Contextos de tipo "tengo registro", "con registro", etc.
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:registro|r\.?c\.?))|"
                      # Para capturar escenarios como "mi cédula es X y registro Y"
                      r"(?:(?:y|,)(?:\s+)(?:registro|r\.?c\.?))|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:registro|rc|r\.c\.|r\s*c)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{10,11})", re.IGNORECASE),
            "min_digits": 10,
            "max_digits": 11,
            "allow_letters": True,
            "score": 0.9
        },"PA": {
            "regex": re.compile(r"(?:"
                      # Pasaporte con variantes completas
                      r"(?:pasaporte)|"
                      # Abreviaturas con puntos o sin puntos
                      r"(?:pa\.?)|"
                      # Términos posesivos - ampliados para incluir más contextos
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:pasaporte|pa\.?)(?:\s+(?:es|son|:))?)|"
                      # Contextos de tipo "tengo pasaporte", "con pasaporte", etc.
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:pasaporte|pa\.?))|"
                      # Para capturar escenarios como "mi cédula es X y pasaporte Y"
                      r"(?:(?:y|,)(?:\s+)(?:pasaporte|pa\.?))|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:pasaporte|pa|p\.a\.)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{6,8})", re.IGNORECASE),
            "pattern": r"^[A-Za-z0-9]{6,8}$",
            "score": 0.9
        },        "NIT": {
            "regex": re.compile(r"(?:"
                      # NIT con variantes completas
                      r"(?:numero\s+de\s+identificacion\s+tributaria)|"
                      # Abreviaturas con puntos o sin puntos
                      r"(?:n\.?i\.?t\.?)|"
                      # Términos posesivos - ampliados para incluir más contextos
                      r"(?:(?:mi|su|la|el)(?:\s+)(?:nit|n\.?i\.?t\.?)(?:\s+(?:es|son|:))?)|"
                      # Contextos de tipo "tengo nit", "con nit", etc.
                      r"(?:(?:tengo|tiene|con|número|numero)(?:\s+)(?:nit|n\.?i\.?t\.?))|"
                      # Para capturar escenarios como "mi cédula es X y nit Y"
                      r"(?:(?:y|,)(?:\s+)(?:nit|n\.?i\.?t\.?))|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:nit|n\.i\.t\.|n\s*i\s*t)(?:\s*)?(?::|=|es|es:|número|numero|son))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Za-z0-9]{9,10}(?:[\s-]*[A-Za-z0-9]{1})?)", re.IGNORECASE),
            "min_digits": 9,
            "max_digits": 11,
            "allow_letters": True,
            "score": 0.9
        },
        "PEP": {
            "regex": re.compile(r"(?:"
                      # PEP con variantes completas
                      r"(?:permiso\s+especial\s+de\s+permanencia)|"
                      # Abreviaturas
                      r"(?:pep)|"
                      # Términos posesivos
                      r"(?:mi(?:\s+)(?:permiso|pep)(?:\s+es)?)|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:pep|permiso)(?:\s*)?(?::|=|es|es:|número|numero))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?([A-Z0-9]{5,15})", re.IGNORECASE),
            "min_length": 5,
            "max_length": 15,
            "score": 0.9
        },
        "DOTTED_CC": {
            "regex": re.compile(r"(?:"
                      # Cédula de ciudadanía con variantes completas
                      r"(?:(?:cedula|cédula)(?:\s+de\s+ciudadan[ií]a)?)|"
                      # Abreviaturas con puntos o sin puntos
                      r"(?:c\.?\s*c\.?)|"
                      # Términos posesivos
                      r"(?:mi(?:\s+)(?:cedula|cédula|c\.?c\.?)(?:\s+es)?)|"
                      # Expresiones con dos puntos o igual
                      r"(?:(?:cedula|cédula|cc|c\.c\.|c\s*c)(?:\s*)?(?::|=|es|es:|número|numero))"
                      r")(?:\s*#?\s*|\s*:\s*|\s*-\s*|\s+|\s*numero\s*|\s*n[uú]mero\s*)?(?:\d{1,2}\.)?(?:\d{3}\.){1,2}\d{3}", re.IGNORECASE),
            "score": 0.95
        }
    }
      # Patrones de contexto compilados para mayor eficiencia
    CONTEXT_PATTERNS = [
        # Cédula de Ciudadanía - CC
        (re.compile(r"(?:"
                  # Formato completo
                  r"c[eé]dula\s+(?:de\s+)?ciudadan[ií]a|"
                  # Abreviaturas
                  r"c\.?c\.?|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|la|el|este|esta|ese|esa|aquel|aquella)\s+(?:c[eé]dula|cc)|"
                  # Número de cédula
                  r"n[úu]mero\s+de\s+(?:c[eé]dula|cc)|"
                  # Expresiones con dos puntos o igual  
                  r"c[eé]dula(?:\s*)?(?::|=|es|es:)|"
                  # ID nacional
                  r"(?:documento|id)\s+nacional"
                  r")", re.IGNORECASE), 0.3, "CC"),
        
        # Tarjeta de Identidad - TI
        (re.compile(r"(?:"
                  # Formato completo
                  r"tarjeta\s+(?:de\s+)?identidad|"
                  # Abreviaturas
                  r"t\.?i\.?|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|la|el|este|esta|ese|esa|aquel|aquella)\s+(?:tarjeta|ti)|"
                  # Número de tarjeta
                  r"n[úu]mero\s+de\s+(?:tarjeta|ti)|"
                  # Expresiones con dos puntos o igual
                  r"tarjeta(?:\s*)?(?::|=|es|es:)|"
                  # ID de menor
                  r"documento\s+(?:de\s+)?menor"
                  r")", re.IGNORECASE), 0.3, "TI"),
        
        # Cédula de Extranjería - CE
        (re.compile(r"(?:"
                  # Formato completo
                  r"c[eé]dula\s+(?:de\s+)?extranjer[ií]a|"
                  # Abreviaturas
                  r"c\.?e\.?|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|la|el|este|esta|ese|esa|aquel|aquella)\s+(?:extranjer[ií]a|ce)|"
                  # Número de extranjería
                  r"n[úu]mero\s+de\s+(?:extranjer[ií]a|ce)|"
                  # Expresiones con dos puntos o igual
                  r"extranjer[ií]a(?:\s*)?(?::|=|es|es:)"
                  r")", re.IGNORECASE), 0.3, "CE"),
        
        # Registro Civil - RC
        (re.compile(r"(?:"
                  # Formato completo
                  r"registro\s+civil(?:\s+de\s+nacimiento)?|"
                  # Abreviaturas
                  r"r\.?c\.?|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|el|la|este|esta|ese|esa|aquel|aquella)\s+(?:registro|rc)|"
                  # Número de registro
                  r"n[úu]mero\s+de\s+(?:registro|rc)|"
                  # Expresiones con dos puntos o igual
                  r"registro(?:\s*)?(?::|=|es|es:)"
                  r")", re.IGNORECASE), 0.3, "RC"),
        
        # Pasaporte - PA
        (re.compile(r"(?:"
                  # Formato completo
                  r"pasaporte|"
                  # Abreviaturas
                  r"pa\.?|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|el|la|este|esta|ese|esa|aquel|aquella)\s+(?:pasaporte|pa)|"
                  # Número de pasaporte
                  r"n[úu]mero\s+de\s+(?:pasaporte|pa)|"
                  # Expresiones con dos puntos o igual
                  r"pasaporte(?:\s*)?(?::|=|es|es:)"
                  r")", re.IGNORECASE), 0.3, "PA"),
        
        # NIT - Número de Identificación Tributaria
        (re.compile(r"(?:"
                  # Formato completo
                  r"n[úu]mero\s+de\s+identificaci[óo]n\s+tributaria|"
                  # Abreviaturas
                  r"n\.?i\.?t\.?|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|el|la|este|esta|ese|esa|aquel|aquella)\s+(?:nit)|"
                  # Número de NIT
                  r"n[úu]mero\s+de\s+(?:nit)|"
                  # Expresiones con dos puntos o igual
                  r"nit(?:\s*)?(?::|=|es|es:)|"
                  # ID tributario/fiscal
                  r"identifi(?:caci[óo]n|cador)\s+(?:tributari[oa]|fiscal)"
                  r")", re.IGNORECASE), 0.3, "NIT"),
        
        # PEP - Permiso Especial de Permanencia
        (re.compile(r"(?:"
                  # Formato completo
                  r"permiso\s+especial\s+de\s+permanencia|"
                  # Abreviaturas
                  r"pep|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|el|la|este|esta|ese|esa|aquel|aquella)\s+(?:permiso|pep)|"
                  # Número de permiso
                  r"n[úu]mero\s+de\s+(?:permiso|pep)|"
                  # Expresiones con dos puntos o igual
                  r"permiso(?:\s*)?(?::|=|es|es:)"
                  r")", re.IGNORECASE), 0.3, "PEP"),
        
        # Documento de identidad genérico
        (re.compile(r"(?:"
                  # Términos genéricos
                  r"documento\s+(?:de\s+)?identidad|"
                  r"identificaci[oó]n|"
                  r"\bid\b|"
                  # Expresiones posesivas y atributivas
                  r"(?:mi|su|tu|el|la|este|esta|ese|esa|aquel|aquella)\s+(?:documento|id)|"
                  # Número de documento
                  r"n[úu]mero\s+de\s+(?:documento|identidad|identificaci[óo]n)"
                  r")", re.IGNORECASE), 0.2, "ID"),
    ]
    
    # Patrones de teléfono compilados para mayor eficiencia
    PHONE_PATTERNS = re.compile(
        r"tel[eéè]fono|"
        r"\btel\b|"
        r"celular|"
        r"móvil|"
        r"movil|"
        r"llamar|"
        r"llamame|"
        r"comunica|"
        r"contacta|"
        r"whatsapp|"
        r"comunicarse|"
        r"contacto|"
        r"línea|"
        r"linea",
        re.IGNORECASE
    )
    
    # Patrones de teléfono colombiano compilados para mayor eficiencia
    COLOMBIAN_PHONE_PATTERN = re.compile(
        r"(?:\+57|57)?\s*(?:3\d{2}[\s-]?\d{3}[\s-]?\d{4}|\d{3}[\s-]?\d{4})",
        re.IGNORECASE
    )
    
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = None,
        name: str = None,
    ):
        # Inicializar con valores por defecto
        name = name or "ColombianIDRecognizer"
        supported_entity = supported_entity or self.ENTITY
        
        # Convertir los patrones del diccionario a la lista requerida por el constructor padre
        patterns = patterns or [
            Pattern(name=doc_type.lower(), regex=pattern_info["regex"].pattern, score=pattern_info["score"])
            for doc_type, pattern_info in self.DOCUMENT_PATTERNS.items()
        ]
        
        # Contexto: palabras relacionadas con documentos de identidad
        context = context or [
            "documento", "identificación", "identidad", "cédula", "cedula",
            "tarjeta", "pasaporte", "registro", "civil", "extranjería",
            "extranjeria", "permiso", "permanencia", "visa", "número", "numero",
            "id", "nit", "rut", "documento nacional", "cc", "ti", "ce", "rc", "pa", "pep",
            "ciudadanía", "ciudadania", "colombiano", "colombiana", "identificacion"
        ]
        
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,            supported_language=supported_language,
            name=name,
        )      # Lista de palabras comunes que podrían ser falsamente detectadas como documentos
    COMMON_WORDS = []
    
    def validate_result(self, pattern_match) -> Tuple[bool, float]:
        """
        Valida si el patrón detectado es realmente un documento de identidad.
        
        Args:
            pattern_match: El match encontrado (puede ser un objeto Match o un string)
            
        Returns:
            Tuple[bool, float]: (es_válido, score)
        """
        try:
            # Extraer el texto del match
            if hasattr(pattern_match, 'group'):
                match_text = pattern_match.group(0)
                # Intentar extraer solo el número del documento
                id_number = pattern_match.group(1) if len(pattern_match.groups()) > 0 else match_text
            elif isinstance(pattern_match, str):
                match_text = pattern_match
                # Buscar el número en el texto usando un patrón más específico para documentos
                id_number_match = re.search(r'(?<![a-zA-Z])\d[\d\.\s-]{5,14}(?!\d)', match_text)
                if id_number_match:
                    id_number = id_number_match.group(0)
                else:
                    id_number = match_text
            else:
                return False, 0.0
            
            # Verificar si el texto coincide con alguna palabra común (falso positivo)
            lower_match = match_text.lower()
            for common_word in self.COMMON_WORDS:
                if common_word.lower() in lower_match:
                    return False, 0.0
                
            # Limpiar el número (quitar espacios, guiones y puntos)
            clean_id = re.sub(r'[\s\-\.]', '', id_number)
              # Verificar si hay indicador claro de tipo de documento - más restrictivo con límites de palabra
            has_doc_indicator = re.search(
                r'(?:\bc[eé]dula\b|\bc\.?c\.?\b|\btarjeta\b|\bt\.?i\.?\b|\bregistro\b|\br\.?c\.?\b|'
                r'\bextranjer[ií]a\b|\bc\.?e\.?\b|\bpasaporte\b|\bpa\.?\b|\bnit\b|\bn\.?i\.?t\.?\b|'
                r'\bpermiso\b|\bpep\b|\bdocumento\s+(?:de\s+)?identidad\b)', 
                match_text.lower()
            )
            
            # Score inicial basado en la presencia de indicador de documento
            # Sin indicador claro, asignamos un score bajo para evitar falsos positivos
            base_score = 0.75 if has_doc_indicator else 0.4
            
            # Si no hay indicador claro y parece un teléfono, rechazarlo
            if not has_doc_indicator:
                # Verificar si tiene formato de celular colombiano (3XX-XXX-XXXX)
                if (len(clean_id) == 10 and clean_id.startswith('3') and clean_id.isdigit()):
                    return False, 0.0
                
                # Verificar si tiene formato de teléfono fijo (7 dígitos)
                if len(clean_id) == 7 and clean_id.isdigit():
                    return False, 0.0
                
                # Verificar prefijos de teléfono internacional
                if re.search(r'^(?:\+57|57|03)', clean_id):
                    return False, 0.0
                
                # Verificar formato internacional general
                if re.search(r'^\+\d{1,3}\s?\d+', clean_id):
                    return False, 0.0
            
            # Debe contener al menos un dígito o una letra
            if not re.search(r'[\dA-Za-z]', clean_id):
                return False, 0.0
                  # Verificar longitud y formato según tipo de documento
            num_chars = len(clean_id)
            
            # Determinar tipo de documento a partir del contexto
            doc_type = "UNKNOWN"
            
            # Buscar indicadores de tipo específico de documento
            cc_indicator = re.search(r'c[eé]dula\s+(?:de\s+)?ciudadan[ií]a|c\.?c\.?', match_text.lower())
            ti_indicator = re.search(r'tarjeta\s+(?:de\s+)?identidad|t\.?i\.?', match_text.lower())
            ce_indicator = re.search(r'c[eé]dula\s+(?:de\s+)?extranjer[ií]a|c\.?e\.?', match_text.lower())
            rc_indicator = re.search(r'registro\s+civil|r\.?c\.?', match_text.lower())
            pa_indicator = re.search(r'pasaporte|pa\.?', match_text.lower())
            nit_indicator = re.search(r'nit|n\.?i\.?t\.?', match_text.lower())
            
            # Asignar tipo según indicadores
            if cc_indicator:
                doc_type = "CC"
                # Verificar longitud de cédula (7-10 caracteres)
                if not (7 <= num_chars <= 10):
                    return False, 0.0
            elif ti_indicator:
                doc_type = "TI"
                # Verificar longitud de tarjeta de identidad (10-11 caracteres)
                if not (10 <= num_chars <= 11):
                    return False, 0.0
            elif ce_indicator:
                doc_type = "CE"
                # Verificar longitud de cédula de extranjería (6-8 caracteres)
                if not (5 <= num_chars <= 8):
                    return False, 0.0
            elif rc_indicator:
                doc_type = "RC"
                # Verificar longitud de registro civil (10-11 caracteres)
                if not (10 <= num_chars <= 11):
                    return False, 0.0
            elif pa_indicator:
                doc_type = "PA"
                # Verificar formato de pasaporte (longitud adecuada)
                if not (6 <= num_chars <= 7):
                    return False, 0.0
            elif nit_indicator:
                doc_type = "NIT"
                # Verificar longitud de NIT (9-11 caracteres incluyendo dígito de verificación)
                if not (9 <= num_chars <= 11):
                    return False, 0.0
            else:
                # Si no hay indicador específico, verificar longitudes estándar
                if num_chars < 6 or num_chars > 12:
                    return False, 0.0
            
            # Verificar características adicionales para aumentar la confianza
            # Presencia de indicadores de documento aumenta el score
            score_adjustments = 0.0
            
            # Si el formato tiene puntos como separadores (ejemplo: 1.234.567) 
            if re.search(r'\d{1,3}\.\d{3}(\.\d{3})?', match_text):
                score_adjustments += 0.15
                
            # Si el número está precedido por tipo de documento
            if has_doc_indicator:
                score_adjustments += 0.15
                
            # Si hay dos puntos o igual antes del número
            if re.search(r'[:=]', match_text):
                score_adjustments += 0.1
                
            # Si el formato incluye frases posesivas (mi cédula, su cédula)
            if re.search(r'(?:mi|su|tu|la|el|este|esta|ese|esa)\s+(?:c[eé]dula|tarjeta|registro|pasaporte|documento)', match_text.lower()):
                score_adjustments += 0.2
              # Identificar tipo de documento a partir del texto
            doc_type = self._identify_document_type(match_text.lower())
            
            # Validar según el tipo identificado
            if doc_type and doc_type in self.DOCUMENT_PATTERNS:
                pattern_info = self.DOCUMENT_PATTERNS[doc_type]
                  # Validación de pasaporte (formato especial)
                if doc_type == "PA" and "pattern" in pattern_info:
                    # Para pasaportes podemos ser más flexibles con el formato
                    if not (6 <= len(clean_id) <= 7):
                        return False, 0.0
                # Validación por rango de caracteres
                elif "min_digits" in pattern_info and "max_digits" in pattern_info:
                    # Usando la longitud del ID para validar independientemente de si son letras o números
                    if not (pattern_info["min_digits"] <= len(clean_id) <= pattern_info["max_digits"]):
                        return False, 0.0
            
            # Verificar características adicionales para aumentar la confianza
            # Presencia de indicadores de documento aumenta el score
            score_adjustments = 0.0
            
            # Si el formato tiene puntos como separadores (ejemplo: 1.234.567) 
            if re.search(r'\d{1,3}\.\d{3}(\.\d{3})?', match_text):
                score_adjustments += 0.15
                
            # Si el número está precedido por tipo de documento
            if has_doc_indicator:
                score_adjustments += 0.15
                
            # Si hay dos puntos o igual antes del número
            if re.search(r'[:=]', match_text):
                score_adjustments += 0.1
                
            # Si el formato incluye frases posesivas (mi cédula, su cédula)
            if re.search(r'(?:mi|su|tu|la|el|este|esta|ese|esa)\s+(?:c[eé]dula|tarjeta|registro|pasaporte|documento)', match_text.lower()):
                score_adjustments += 0.2
            
            # Calcular score final
            final_score = min(1.0, base_score + score_adjustments)
            
            return True, final_score
            
        except Exception:
            return False, 0.0
    
    def _identify_document_type(self, text: str) -> Optional[str]:
        """
        Identifica el tipo de documento a partir del texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Optional[str]: Tipo de documento o None si no se identifica
        """        # Buscar coincidencias en el texto para cada tipo de documento
        for doc_type, pattern_info in self.DOCUMENT_PATTERNS.items():
            if re.search(pattern_info["regex"].pattern, text, re.IGNORECASE):
                return doc_type
        
        return None
    
    def analyze_id_context(self, text: str, start: int, end: int) -> Tuple[float, str]:
        """
        Analiza el contexto alrededor del ID para mejorar la detección.
        
        Args:
            text: Texto completo
            start: Posición inicial del ID
            end: Posición final del ID
            
        Returns:
            Tuple[float, str]: (score_adicional, tipo_documento)
        """
        # Obtener contexto amplio para mejor análisis
        context_start = max(0, start - 100)
        context_end = min(len(text), end + 50)
        context_text = text[context_start:context_end].lower()
        
        # Obtener contexto más cercano para palabras clave
        close_context_start = max(0, start - 30)
        close_context_end = min(len(text), end + 15)
        close_context = text[close_context_start:close_context_end].lower()
        
        # Descartar si es claramente contexto de teléfono sin indicador de documento
        if (self.PHONE_PATTERNS.search(close_context) and 
            not re.search(r'(?:c[eé]dula|cc|ti|ce|rc|nit|pep|pasaporte|documento)', close_context)):
            return -1.0, "NOT_DOCUMENT"
        
        # Patrones lingüísticos fuertes (expresiones directas sobre documentos)
        strong_patterns = [
            # Expresiones de presentación personal
            (r'(?:me\s+identific(?:o|a)|mi\s+nombre\s+es|soy)[^.]{1,30}(?:con|mediante|usando)[^.]{1,15}(?:c[eé]dula|documento|id)', 0.35, "CC"),
            # Conjugaciones verbales directas
            (r'(?:presento|muestro|adjunto|anexo|entrego|aporto)[^.]{1,30}(?:c[eé]dula|documento|id)', 0.3, "CC"),
            # Fórmulas oficiales
            (r'(?:identific(?:ado|ada)|acredit(?:ado|ada))[^.]{1,30}(?:con|mediante|por)[^.]{1,15}(?:c[eé]dula|documento|id)', 0.35, "CC")
        ]
        
        # Verificar patrones lingüísticos fuertes
        for pattern, score, id_type in strong_patterns:
            if re.search(pattern, context_text, re.IGNORECASE):
                return score, id_type
                
        # Verificar expresiones posesivas
        possessive_patterns = [
            (r'(?:mi|su|tu|la)\s+c[eé]dula(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.3, "CC"),
            (r'(?:mi|su|tu|la)\s+tarjeta(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.3, "TI"),
            (r'(?:mi|su|tu|el)\s+registro(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.3, "RC"),
            (r'(?:mi|su|tu|el)\s+pasaporte(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.3, "PA"),
            (r'(?:mi|su|tu|la)\s+extranjer[ií]a(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.3, "CE"),
            (r'(?:mi|su|tu|el)\s+nit(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.3, "NIT"),
            (r'(?:mi|su|tu|el)\s+documento(?:\s+(?:es|d[ei]|n[uú]mero))?', 0.25, "ID")
        ]
        
        # Verificar expresiones posesivas
        for pattern, score, id_type in possessive_patterns:
            if re.search(pattern, close_context, re.IGNORECASE):
                return score, id_type
        
        # Verificar cada patrón de contexto estándar
        for pattern, score, id_type in self.CONTEXT_PATTERNS:
            if pattern.search(close_context):
                # Si está en el contexto cercano, aumentar ligeramente el score
                return score + 0.05, id_type
        
        # Verificar estructuras de formularios
        form_patterns = [
            (r'(?:c[eé]dula|documento|id)[^:]{0,10}:', 0.25, "CC"),
            (r'n[uú]mero(?:\s+de)?(?:\s+documento|\s+id|\s+identificaci[oó]n)?[^:]{0,10}:', 0.2, "ID")
        ]
        
        for pattern, score, id_type in form_patterns:
            if re.search(pattern, context_text, re.IGNORECASE):
                return score, id_type
        
        # Si no se encontró ningún patrón específico pero hay dígitos en el formato esperado
        if re.search(r'\d{6,10}', text[start:end]):
            return 0.1, "UNKNOWN"
            
        # Si no se encontró ningún patrón específico
        return 0.0, "UNKNOWN"
    
    def analyze(self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None) -> List[RecognizerResult]:
        """
        Analiza el texto para encontrar documentos de identidad colombianos.
        
        Args:
            text: Texto a analizar
            entities: Lista de entidades a buscar
            nlp_artifacts: Artefactos NLP opcionales
            
        Returns:
            List[RecognizerResult]: Lista de resultados del reconocedor
        """
        # Obtener resultados base con la implementación del padre
        results = super().analyze(text, entities, nlp_artifacts)
        
        enhanced_results = []
        for result in results:
            # Extraer el texto identificado
            start, end = result.start, result.end
            id_text = text[start:end]
              # Verificar contexto extendido para detectar teléfonos y palabras comunes
            extended_start = max(0, start - 50)
            extended_end = min(len(text), end + 50)
            extended_context = text[extended_start:extended_end].lower()
            
            # Descartar si es claramente un teléfono por contexto y formato
            if self.PHONE_PATTERNS.search(extended_context) and self.COLOMBIAN_PHONE_PATTERN.search(id_text):
                continue
                
            # Verificar si el texto coincide con alguna palabra común (falso positivo)
            detected_text = text[start:end].lower()
            if any(common_word.lower() in detected_text for common_word in self.COMMON_WORDS):
                continue
            
            # Validar el resultado
            is_valid, adjusted_score = self.validate_result(id_text)
            if not is_valid:
                continue
                
            # Analizar contexto para refinar
            context_score, doc_type = self.analyze_id_context(text, start, end)
            
            # Verificar que haya un indicador explícito de documento en el contexto cercano
            has_explicit_indicator = False
            close_start = max(0, start - 30)
            close_end = min(len(text), end + 10)
            close_context = text[close_start:close_end].lower()
            
            explicit_indicators = [
                r"\bc[eé]dula\b", r"\bc\.?c\.?\b", r"\btarjeta\b", r"\bt\.?i\.?\b",
                r"\bregistro\b", r"\br\.?c\.?\b", r"\bextranjer[ií]a\b", r"\bc\.?e\.?\b",
                r"\bpasaporte\b", r"\bpa\.?\b", r"\bnit\b", r"\bn\.?i\.?t\.?\b"
            ]
            
            for indicator in explicit_indicators:
                if re.search(indicator, close_context):
                    has_explicit_indicator = True
                    break
                    
            # Si no hay indicador explícito y el score de contexto es bajo, descartar
            if not has_explicit_indicator and context_score < 0.2:
                continue
            
            # Verificar si está en un contexto de listado de documentos (como "mi cédula es X y pasaporte Y")
            extended_start = max(0, start - 100)  # Ampliamos el contexto para capturar frases más complejas
            extended_end = min(len(text), end + 100)
            extended_context = text[extended_start:extended_end].lower()
            
            # Buscar patrones que indican listado de documentos
            list_patterns = [
                r"(?:(?:mi|su|la)\s+)?(?:cedula|cédula|c\.?c\.?).+(?:y|,)\s+(?:pasaporte|tarjeta|registro|nit)",
                r"(?:tengo|tiene)\s+(?:cedula|cédula|c\.?c\.?).+(?:y|también|además)\s+(?:pasaporte|tarjeta)",
                r"(?:mis|sus)\s+documentos\s+(?:son|incluyen)"
            ]
            
            # Si encontramos un patrón de listado, aumentamos el score del contexto
            for pattern in list_patterns:
                if re.search(pattern, extended_context, re.IGNORECASE):
                    context_score += 0.15
                    break
              # Descartar si el contexto indica que no es documento
            if context_score < 0 or doc_type == "NOT_DOCUMENT":
                continue
            
            # Factor de ajuste basado en si tenemos un indicador explícito
            indicator_factor = 0.15 if has_explicit_indicator else -0.1
                
            # Combinar scores (limitar a 0.95 para evitar falsos positivos con score muy alto)
            final_score = min(0.95, adjusted_score + context_score + indicator_factor)
            
            # Para contextos de listas de documentos, usar un umbral adecuado
            if any(re.search(pattern, extended_context, re.IGNORECASE) for pattern in list_patterns) and has_explicit_indicator:
                min_score = 0.6  # Umbral para listas de documentos
            else:
                min_score = 0.65  # Umbral más alto para exigir más precisión
                
            # Descartar si el score final es bajo
            if final_score < min_score:
                continue
            
            # Crear resultado mejorado con tipo de documento
            entity_type = f"{self.ENTITY}_{doc_type}" if doc_type != "UNKNOWN" else self.ENTITY
            
            enhanced_results.append(RecognizerResult(
                entity_type=entity_type,
                start=result.start,
                end=result.end,
                score=final_score,
                analysis_explanation=result.analysis_explanation
            ))
        
        return enhanced_results


def create_colombian_recognizers() -> List[PatternRecognizer]:
    """
    Crea todos los reconocedores colombianos disponibles.
    
    Returns:
        List[PatternRecognizer]: Lista de reconocedores para documentos colombianos
    """
    # Reconocedor principal que maneja todos los tipos de documentos
    main_recognizer = ColombianIDRecognizer()
      # Para compatibilidad con código existente, crear reconocedores individuales
    recognizers = [main_recognizer]
    
    # Mapa de tipos de documento y sus configuraciones
    individual_recognizers = {
        "CC_COLOMBIANA": {
            "pattern": ColombianIDRecognizer.DOCUMENT_PATTERNS["CC"]["regex"].pattern,
            "context": ["cédula", "cedula", "cc", "c.c.", "ciudadanía", "identidad"]
        },
        "TI_COLOMBIANA": {
            "pattern": ColombianIDRecognizer.DOCUMENT_PATTERNS["TI"]["regex"].pattern,
            "context": ["tarjeta", "identidad", "TI", "T.I.", "menor"]
        },
        "CE_COLOMBIANA": {
            "pattern": ColombianIDRecognizer.DOCUMENT_PATTERNS["CE"]["regex"].pattern,
            "context": ["extranjería", "extranjeria", "CE", "C.E.", "extranjero"]
        }
    }
    
    # Crear reconocedores individuales
    for entity, config in individual_recognizers.items():
        recognizers.append(PatternRecognizer(
            supported_entity=entity,
            patterns=[Pattern(name=entity.lower(), regex=config["pattern"], score=0.85)],
            context=config["context"],
            supported_language="es"
        ))
    
    return recognizers