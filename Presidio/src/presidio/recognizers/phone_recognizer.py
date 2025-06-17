from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts

# Importar el reconocedor de documentos colombianos
try:
    from src.services.recognizers.recognizer_co_identity_number import ColombianIDRecognizer
except ImportError:
    # Si no está disponible, crear una clase dummy
    class ColombianIDRecognizer:
        def __init__(self):
            pass
        def analyze_id_context(self, text, start, end):
            return 0, "UNKNOWN"
        def validate_result(self, text):
            return False, 0.0

class PhoneRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para números telefónicos latinoamericanos.
    
    Este reconocedor utiliza expresiones regulares para detectar diversos formatos
    de números telefónicos comunes en Latinoamérica, incluyendo códigos de país,
    códigos de área y diferentes formatos de separación.
    """
    
    # Identificador para el reconocedor
    ENTITY = "PHONE_NUMBER"
    
    # Patrones de números telefónicos latinoamericanos
    BASIC_PHONE_PATTERN = r"""(?:(?:\+|00)?(?:501|502|503|504|505|506|507|509|51|52|53|54|55|56|57|58|591|592|593|594|595|596|597|598|599|1)?[ -]?)?(?:\(?\d{1,4}\)?[ -]?)?(?:\d{1,4}[ -]?){1,3}\d{1,4}"""
    
    # Patrón para formatos específicos comunes en Latinoamérica
    LATAM_FORMATS = r"""(?:
        (?:\+|00)?(?:5\d{1,2}|1)[ -]?(?:\d[ -]?){5,13} |              # Con código país +52, +54, etc.
        \(?\d{2,5}\)?[ -]?(?:\d{3,4}[ -]?)+\d{2,4} |                  # Formato (área) número
        \d{2,4}[ -]?\d{2,4}[ -]?\d{2,4}[ -]?\d{0,4}                   # Formato simple separado
    )"""
    
    # Patrón mejorado para teléfonos internacionales con el símbolo +
    INTL_CODE_PATTERN = re.compile(r"(?:\+|00)(?:501|502|503|504|505|506|507|509|51|52|53|54|55|56|57|58|591|592|593|594|595|596|597|598|599|1)[\s-]?\d", re.VERBOSE)
    
    # Patrón compilado para celulares colombianos
    COLOMBIAN_CELL_PATTERN = re.compile(r"(?:\+57|57)?[\s-]?3\d{2}[\s-]?\d{3}[\s-]?\d{4}", re.VERBOSE)
    
    # Patrón específico para detectar números con indicativo internacional (con +)
    INTL_PLUS_PATTERN = re.compile(r"\+\d{1,4}[\s-]?\d{1,3}[\s-]?\d{3,4}[\s-]?\d{2,4}", re.VERBOSE)
    
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = None,
        name: str = None,
    ):
        # Definir patrones de detección
        patterns = [
            Pattern(
                name="intl_plus_pattern",
                regex=r"\+\d{1,4}[\s-]?\d{1,3}[\s-]?\d{3,4}[\s-]?\d{2,4}",
                score=0.85,  # Altísima confianza para números con indicativo internacional
            ),
            Pattern(
                name="latam_formats",
                regex=self.LATAM_FORMATS,
                score=0.75,  # Alta confianza para formatos específicos
            ),
            Pattern(
                name="basic_phone_pattern",
                regex=self.BASIC_PHONE_PATTERN,
                score=0.6,   # Confianza moderada para el patrón genérico
            )
        ]
        
        # Contexto: palabras que suelen acompañar a números telefónicos
        context = context if context else [
            "teléfono", "tel", "celular", "móvil", "fijo", 
            "llamar", "contacto", "comuníquese", "whatsapp", "línea",
            "mi número", "mi numero", "mi whatsapp", "mi contacto", "mi cel", 
            "número es", "numero es", "me puedes llamar", "comunícate",
            "escríbeme", "escribeme", "mensaje", "marcación", "marcar"
        ]
        
        # Inicializar con valores por defecto
        name = name if name else "PhoneRecognizer"
        supported_entity = supported_entity if supported_entity else self.ENTITY
        
        # Inicializar el reconocedor de documentos colombianos
        try:
            self.colombian_id_recognizer = ColombianIDRecognizer()
        except Exception:
            self.colombian_id_recognizer = ColombianIDRecognizer()  # Dummy class
        
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )
    
    def validate_result(self, pattern_match, text=None, start=None, end=None) -> Tuple[bool, float]:
        """
        Valida si el patrón detectado es realmente un número telefónico.
        """
        try:
            # Verificar si es un objeto match o un string
            if hasattr(pattern_match, 'group'):
                match_text = pattern_match.group(0)
            elif isinstance(pattern_match, str):
                match_text = pattern_match
            else:
                return False, 0.0
            
            # Limpiar el número (eliminar espacios, guiones, paréntesis)
            clean_number = re.sub(r'[\s\-\(\)\+]', '', match_text)
            
            # Verificar longitud: teléfonos típicos tienen entre 7 y 15 dígitos
            if len(clean_number) < 7 or len(clean_number) > 15:
                return False, 0.0
            
            # Verificar que sea principalmente dígitos (>70%)
            digit_ratio = sum(c.isdigit() for c in match_text) / len(match_text)
            if digit_ratio < 0.7:
                return False, 0.0
            
            # Verificar el contexto para decidir si es un documento o un teléfono
            if text and start is not None and end is not None:
                # Primero verificar si hay indicaciones claras de que es un documento
                if self._is_likely_document(text, start, end, match_text):
                    return False, 0.0
            
            # Score inicial
            score = 0.6
            
            # Si tiene el símbolo + seguido de un número (muy alta probabilidad de ser teléfono)
            if self.INTL_PLUS_PATTERN.search(match_text):
                score = 0.9
                return True, score
            
            # Si tiene formato de celular colombiano (muy probable teléfono)
            if self.COLOMBIAN_CELL_PATTERN.search(match_text):
                score = 0.8
                return True, score
            
            # Si tiene código de país claro (muy probable teléfono)
            if self.INTL_CODE_PATTERN.search(match_text):
                score = 0.85
                return True, score
            
            # Si tiene la longitud típica de un número completo (10-12 dígitos)
            if 10 <= len(clean_number) <= 12:
                score += 0.1
            
            # Si tiene separadores típicos de teléfono
            if re.search(r'\d{2,4}[\s-]\d{2,4}[\s-]\d{2,4}', match_text):
                score += 0.1
                
            return True, min(0.95, score)
            
        except Exception:
            return False, 0.0
    
    def _is_likely_document(self, text: str, start: int, end: int, match_text: str) -> bool:
        """
        Verifica si el texto detectado es probablemente un documento de identidad.
        """
        # Si el número comienza con un '+', es casi seguro un teléfono, no un documento
        if '+' in match_text:
            return False
            
        # Obtener contexto extendido
        context_start = max(0, start - 50)
        context_end = min(len(text), end + 50)
        context_text = text[context_start:context_end].lower()
        
        # Verificar palabras clave de teléfonos en el contexto (prioridad alta)
        phone_strong_indicators = [
            "mi número es", "mi numero es", "mi whatsapp", "mi cel es",
            "llamar al", "contactar al", "comunícate al", "escribir al",
            "teléfono:", "telefono:", "celular:", "móvil:", "movil:"
        ]
        
        for term in phone_strong_indicators:
            if term in context_text:
                # Si hay términos muy específicos de teléfono, es casi seguro que no es un documento
                return False
        
        # Verificar palabras clave de documentos en el contexto
        document_indicators = [
            "cédula", "cedula", "c.c.", "cc ", "cc:", "c c", "c. c.",
            "documento", "identidad", "identificación", "identificacion",
            "tarjeta", "ti ", "ti:", "t.i.", "registro civil", "rc ", "rc:",
            "pasaporte", "pa ", "pa:", "extranjería", "ce ", "ce:", "c.e.",
            "nit", "n.i.t.", "permiso", "pep", "visa"
        ]
        
        for term in document_indicators:
            if term in context_text:
                # Si hay términos muy específicos de documentos, es casi seguro que no es un teléfono
                return True
        
        # Consultar al reconocedor de documentos para analizar el contexto
        try:
            context_score, doc_type = self.colombian_id_recognizer.analyze_id_context(text, start, end)
            if context_score > 0 and doc_type != "UNKNOWN":
                # Si el contexto indica que es un documento, no es un teléfono
                return True
        except Exception:
            pass
        
        # Verificar si el formato coincide con un documento colombiano típico
        try:
            is_valid_doc, _ = self.colombian_id_recognizer.validate_result(match_text)
            if is_valid_doc:
                # Si el reconocedor colombiano lo valida como documento, necesitamos más análisis
                
                # Limpiar número para análisis
                clean_number = re.sub(r'[\s\-\.]', '', match_text)
                
                # Verificar características específicas de documentos colombianos
                # Cédulas típicamente tienen 10 dígitos y empiezan con 1
                if len(clean_number) == 10 and clean_number.startswith('1'):
                    # Verificar si hay algún indicio de que sea teléfono
                    phone_indicators = ["tel", "celular", "móvil", "llamar", "whatsapp"]
                    has_phone_context = any(indicator in context_text for indicator in phone_indicators)
                    
                    # Si no hay contexto de teléfono, probablemente es un documento
                    if not has_phone_context:
                        return True
                
                # Verificar si tiene prefijos claros de teléfono
                has_phone_prefix = bool(re.match(r'^\+\d{2}|^\(\d{2,3}\)|^3\d{2}', clean_number))
                if not has_phone_prefix and len(clean_number) >= 8 and len(clean_number) <= 10:
                    # Sin prefijo telefónico claro y con longitud típica de documento, 
                    # es probablemente un documento
                    return True
        except Exception:
            pass
                
        return False
    
    def analyze_context(self, text: str, start: int, end: int) -> float:
        """
        Analiza el contexto alrededor del número para mejorar la detección.
        """
        # Obtener contexto (20 caracteres antes y después)
        context_start = max(0, start - 20)
        context_end = min(len(text), end + 20)
        context_text = text[context_start:context_end].lower()
        
        score_adjustment = 0.0
        
        # Patrones de contexto comunes para números telefónicos
        context_patterns = [
            (r'(?:tel[éeèf]fono|tel)[^a-z0-9]*', 0.25),
            (r'(?:celular|móvil|movil)[^a-z0-9]*', 0.25),
            (r'(?:llamar|contacto)[^a-z0-9]*', 0.2),
            (r'(?:whatsapp|línea|linea)[^a-z0-9]*', 0.2),
            (r'(?:comunica|contacta)[^a-z0-9]*', 0.15),
            (r'mi(?:\s+)(?:número|numero|whatsapp|contacto|cel)[^a-z0-9]*(?:es)?', 0.3),
            (r'(?:número|numero)(?:\s+)(?:es|:)', 0.3),
            (r'(?:me\s+puedes?\s+(?:llamar|contactar|escribir))[^a-z0-9]*(?:al|en)?', 0.25),
            (r'(?:escríbeme|escribeme|contáctame|contactame)[^a-z0-9]*(?:al|en)?', 0.25),
        ]
        
        # Verificar cada patrón de contexto
        for pattern, score in context_patterns:
            if re.search(pattern, context_text):
                score_adjustment += score
                break  # Solo aplicar el ajuste más alto
        
        return min(0.25, score_adjustment)
    
    def analyze(self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None) -> List[RecognizerResult]:
        """
        Analiza el texto para encontrar números telefónicos.
        """
        # 1. Primero, analizar el texto con el reconocedor de documentos colombianos
        document_results = []
        try:
            document_results = self.colombian_id_recognizer.analyze(text, [self.colombian_id_recognizer.ENTITY], nlp_artifacts)
        except Exception:
            pass
        
        # Crear un conjunto de rangos donde se detectaron documentos
        document_ranges = set()
        for result in document_results:
            # Añadir todas las posiciones desde start hasta end
            for pos in range(result.start, result.end + 1):
                document_ranges.add(pos)
        
        # 2. Obtener resultados base mediante patrones
        results = super().analyze(text, entities, nlp_artifacts)
        
        enhanced_results = []
        for result in results:
            # Extraer posiciones
            start, end = result.start, result.end
            phone_text = text[start:end]
            
            # Verificar si el resultado se solapa con algún documento detectado
            overlaps_with_document = any(pos in document_ranges for pos in range(start, end + 1))
            if overlaps_with_document:
                # Si ya fue detectado como documento, saltarlo
                continue
            
            # Si no se solapa, verificar si es un teléfono válido
            is_valid, adjusted_score = self.validate_result(phone_text, text, start, end)
            if not is_valid:
                continue
                
            # Analizar contexto para refinar
            context_score = self.analyze_context(text, start, end)
            
            # Combinar scores (limitar a 0.95)
            final_score = min(0.95, adjusted_score + context_score)
            
            # Verificar umbral mínimo
            if final_score < 0.6:
                continue
                
            # Crear resultado mejorado
            enhanced_result = RecognizerResult(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=final_score,
                analysis_explanation=result.analysis_explanation
            )
            enhanced_results.append(enhanced_result)
            
        return enhanced_results