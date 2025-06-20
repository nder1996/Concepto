# colombian_location_recognizer.py - SIGUIENDO EL MISMO PATRÓN
from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
import logging
from typing import List, Tuple
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger(__name__)

class ColombianLocationRecognizer(PatternRecognizer):
    """
    Reconocedor simplificado para ubicaciones colombianas.
    Siguiendo el mismo patrón que ColombianIDRecognizer.
    """

    ENTITY = "COLOMBIAN_LOCATION"
    SUPPORTED_LANGUAGE = "es"
    supported_entity = ENTITY

    # Configuración SIMPLIFICADA
    _SIMPLE_CONFIG = {
        # Ventana de contexto reducida
        "context_window": 30,
        
        # Solo palabras realmente problemáticas
        "excluded_words": ["persona", "usuario", "cliente", "empresa", "documento", "carrera profesional", "carrera universitaria"],
        
        # Filtros para falsos positivos
        "false_positive_patterns": [
            r"identificac",
            r"documento",
            r"email",
            r"teléfono",
            r"carrera\s+(?:profesional|universitaria|de)",
            r"calle\s+(?:de\s+la|principal|mayor)",
            r"avenida\s+(?:de\s+los|principal)"
        ]
    }

    # Patrones específicos de direcciones colombianas - MEJORADOS
    _ADDRESS_INDICATORS = [
        # Vías urbanas básicas (con números y letras)
        r'\b(?:calle|carrera|avenida|cra|cr|av|cl)\s+\d+[a-z]?(?:\s*bis|\s*ter|\s*quad)?(?:\s*[a-z])?',
        # Vías especiales abreviadas
        r'\b(?:transversal|diagonal|tv|dg)\s+\d+[a-z]?(?:\s*bis|\s*ter|\s*quad)?(?:\s*[a-z])?',
        # Vías especiales completas
        r'\b(?:autopista|circunvalar|pasaje|paseo|callejón|callejon|vía|via)\s+[a-záéíóúñ\s\-]{3,40}',
        # Numeraciones con # y -
        r'#\s*\d+[a-z]?\s*[-–]\s*\d+[a-z]?',                # #13-47, #8A-55
        r'#\s*\d+[a-z]?(?:\s+[-–]\s+\d+[a-z]?)?',           # # 69 - 11
        # Numeraciones con No., Nro., Núm.
        r'\b(?:no|nro|núm|num)\.?\s*\d+[a-z]?\s*[-–]\s*\d+[a-z]?',
        # Complementos urbanos
        r'\b(?:apartamento|apto|apt|piso|oficina|of|local|lc|casa|interior)\s+\d+[a-z]?',
        r'\b(?:torre|bloque|bl|etapa|manzana|mz|lote)\s+\d+[a-z]?',
        # Centros comerciales y empresariales
        r'\b(?:centro\s+comercial|cc|c\.c\.|centro\s+empresarial|ce|c\.e\.)\s+[a-záéíóúñ\s]{3,40}',
        r'\b(?:edificio|torre|galería|galeria|plaza|terminal)\s+[a-záéíóúñ\s]{3,40}',
        # Rurales
        r'\b(?:vereda|vda|corregimiento|corr)\s+[a-záéíóúñ\s]{3,30}(?:\s+(?:km|kilómetro|kilometro)\s+\d{1,3})?',
        r'\b(?:finca|hacienda|hda|predio|parcela)\s+[a-záéíóúñ\s]{3,30}',
        # Sectores y barrios
        r'\b(?:barrio|br|sector|zona|urbanización|urbanizacion|ciudadela)\s+[a-záéíóúñ\s]{3,30}',
        # Códigos postales con contexto
        r'\b(?:código\s+postal|codigo\s+postal|postal|cp|c\.p\.)\s*:?\s*\d{6}\b',
        # Kilómetros en vías
        r'\bkm\s+\d{1,4}(?:\s*\+\s*\d{1,4})?'               # Km 245, Km 15+500
    ]

    # Configuración COMPLETA de direcciones colombianas (siguiendo el patrón simplificado)
    _LOCATIONS = {
        "ADDRESS_FULL": {
            "name": "Dirección Completa",
            "keywords": ["dirección", "direccion", "domicilio", "residencia", "ubicado en", "vive en"],
            "pattern": r"(?i)\b(?:calle|carrera|avenida|transversal|diagonal|cra|cr|av|cl|tv|dg)\s+\d{1,4}(?:\s*bis|\s*ter|\s*[abcdef])?\s*(?:#|no\.?|nro\.?|núm\.?)\s*\d{1,4}(?:\s*[-–]\s*\d{1,4})?(?:\s+(?:apartamento|apto|apt|piso|oficina|local|casa|interior)\s+\d{1,4})?",
            "score": 0.95
        },
        "ADDRESS_SIMPLE": {
            "name": "Dirección Simple",
            "keywords": ["dirección", "direccion", "domicilio", "ubicación"],
            "pattern": r"(?i)\b(?:calle|carrera|avenida|transversal|diagonal|cra|cr|av|cl|tv|dg)\s+\d{1,4}(?:\s*bis|\s*ter|\s*[abcdef])?",
            "score": 0.85
        },
        "ADDRESS_RURAL": {
            "name": "Dirección Rural",
            "keywords": ["vereda", "corregimiento", "finca", "hacienda", "predio", "parcela"],
            "pattern": r"(?i)\b(?:vereda|corregimiento|finca|hacienda|predio|parcela)\s+[a-záéíóúñ\s]{3,30}(?:\s+km\s+\d{1,3})?",
            "score": 0.90
        },
        "ADDRESS_COMMERCIAL": {
            "name": "Dirección Comercial",
            "keywords": ["centro comercial", "cc", "centro empresarial", "edificio", "torre"],
            "pattern": r"(?i)(?:centro\s+comercial|cc|centro\s+empresarial|edificio|torre)\s+[a-záéíóúñ\s]{3,30}(?:\s+local\s+\d{1,4})?",
            "score": 0.88
        },
        "POSTAL_CODE": {
            "name": "Código Postal",
            "keywords": ["código postal", "codigo postal", "postal", "cp"],
            "pattern": r"\b\d{6}\b",
            "score": 0.80
        }
    }

    def __init__(self, supported_language="es"):
        patterns = self._build_simple_patterns()
        
        super().__init__(
            supported_entity=self.ENTITY,
            patterns=patterns,
            supported_language=supported_language,
            name="ColombianLocationRecognizer"
        )

    def _build_simple_patterns(self) -> List[Pattern]:
        """Construye patrones siguiendo el mismo patrón que ID recognizer"""
        patterns = []
        
        for loc_type, config in self._LOCATIONS.items():
            if not config.get("pattern"):
                continue
                
            # Patrón 1: Con contexto (alta confianza)
            if config.get("keywords"):
                keywords_regex = "|".join(re.escape(k) for k in config["keywords"])
                pattern_with_context = f"\\b(?:{keywords_regex})\\s*[:=]?\\s*({config['pattern']})"
                patterns.append(Pattern(
                    name=f"{loc_type.lower()}_with_context",
                    regex=pattern_with_context,
                    score=config["score"]
                ))
            
            # Patrón 2: Solo dirección (confianza moderada, necesita validación)
            patterns.append(Pattern(
                name=f"{loc_type.lower()}_direct",
                regex=f"\\b({config['pattern']})",
                score=config["score"] - 0.2  # Menor confianza
            ))
        
        return patterns

    def _is_false_positive(self, text: str) -> bool:
        """Detecta falsos positivos mejorado"""
        text_lower = text.lower().strip()
        
        # Filtrar palabras problemáticas exactas
        exact_exclusions = [
            "persona", "usuario", "cliente", "empresa", "documento",
            "carrera profesional", "carrera universitaria", "carrera de",
            "calle principal", "calle de la", "avenida principal", "avenida de los"
        ]
        
        if text_lower in exact_exclusions:
            return True
        
        # Filtrar patrones problemáticos más específicos
        problematic_patterns = [
            r"^(?:identificac|documento|email|teléfono).*",  # Empieza con estas palabras
            r"carrera\s+(?:profesional|universitaria|de\s+\w+)$",  # Carreras académicas
            r"calle\s+(?:de\s+la|principal|mayor)$",  # Calles genéricas
            r"avenida\s+(?:de\s+los|principal)$",  # Avenidas genéricas
            r"^\d{1,3}$",  # Solo números muy cortos
            r"^[a-zA-Z\s]{1,4}$"  # Solo texto muy corto sin números
        ]
        
        for pattern in problematic_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # NO rechazar si tiene características típicas de dirección
        address_characteristics = [
            r'#\s*\d+',  # Tiene numeración con #
            r'\bno\.?\s*\d+',  # Tiene No. o Nro.
            r'\b(?:apartamento|apto|oficina|local|piso|torre|bloque)\s+\d+',  # Complementos
            r'\b(?:km|kilómetro)\s+\d+',  # Kilómetros
            r'\d{6}',  # Código postal
            r'bis|ter|quad',  # Modificadores de vía
            r'[-–]\d+',  # Separador con guión
        ]
        
        has_address_characteristics = any(re.search(pattern, text_lower) 
                                        for pattern in address_characteristics)
        
        if has_address_characteristics:
            return False  # NO es falso positivo si tiene características de dirección
                
        return False  # Por defecto, no rechazar

    def _get_context(self, text: str, start: int, end: int) -> str:
        """Extrae contexto con ventana reducida"""
        window = self._SIMPLE_CONFIG["context_window"]
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].lower()

    def _validate_location(self, loc_text: str, context: str) -> Tuple[bool, str, float]:
        """Validación mejorada siguiendo el mismo patrón"""
        loc_text = loc_text.strip()
        
        # Filtrar falsos positivos
        if self._is_false_positive(loc_text):
            return False, "", 0.0

        candidates = []
        
        # Nivel 1: Buscar por tipo de ubicación con palabras clave en contexto
        for loc_type, config in self._LOCATIONS.items():
            if not config.get("pattern"):
                continue
                
            # Verificar si coincide con el patrón
            if re.search(config["pattern"], loc_text, re.IGNORECASE):
                
                # Contar palabras clave en contexto
                keyword_count = 0
                if config.get("keywords"):
                    keyword_count = sum(1 for keyword in config["keywords"] 
                                     if keyword in context)
                
                if keyword_count > 0:
                    # Mayor confianza con más palabras clave
                    confidence = min(0.98, config["score"] + (keyword_count * 0.03))
                    candidates.append((loc_type, confidence))
                else:
                    # Confianza base sin contexto explícito
                    confidence = config["score"] * 0.8  # Reducir un poco sin contexto
                    candidates.append((loc_type, confidence))

        # Nivel 2: Validación estructural mejorada
        if not candidates:
            if self._looks_like_address(loc_text):
                confidence = self._calculate_address_confidence(loc_text)
                candidates.append(("ADDRESS_INFERRED", confidence))
            elif self._looks_like_postal_code(loc_text, context):
                candidates.append(("POSTAL_CODE_INFERRED", 0.70))

        # Nivel 3: Validación por indicadores específicos
        if not candidates:
            for indicator in self._ADDRESS_INDICATORS:
                if re.search(indicator, loc_text, re.IGNORECASE):
                    confidence = 0.65  # Confianza moderada por estructura
                    candidates.append(("ADDRESS_BY_INDICATOR", confidence))
                    break

        # Retornar el mejor candidato
        if candidates:
            loc_type, confidence = max(candidates, key=lambda x: x[1])
            return True, loc_type, confidence
            
        return False, "", 0.0

    def _calculate_address_confidence(self, text: str) -> float:
        """Calcula confianza basada en características específicas de la dirección"""
        confidence = 0.60  # Base
        text_lower = text.lower()
        
        # Bonificaciones por características específicas
        if re.search(r'#\s*\d+[-–]\d+', text_lower):  # Tiene numeración completa
            confidence += 0.15
        if re.search(r'\b(?:apartamento|apto|oficina|local|piso)\s+\d+', text_lower):  # Tiene complemento
            confidence += 0.10
        if re.search(r'\b(?:calle|carrera|avenida)\s+\d+', text_lower):  # Vía principal estándar
            confidence += 0.10
        if re.search(r'\bbis\b|\bter\b|\bquad\b', text_lower):  # Tiene bis/ter
            confidence += 0.05
        
        return min(0.85, confidence)  # Máximo 0.85 para inferencias

    def _looks_like_address(self, text: str) -> bool:
        """Detecta estructura de dirección colombiana"""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in self._ADDRESS_INDICATORS)

    def _looks_like_postal_code(self, text: str, context: str) -> bool:
        """Detecta códigos postales colombianos mejorado"""
        text_stripped = text.strip()
        # Verificar formato básico de 6 dígitos
        if re.match(r'^\d{6}$', text_stripped):
            return True
        # Contexto con keywords de postal junto al código
        context_lower = context.lower()
        if re.search(r'(?:código postal|codigo postal|postal|cp|c\.p\.)', context_lower) and re.search(r'\b\d{6}\b', text_stripped):
            return True
        return False

    def analyze(self, text: str, entities: List[str] = None, nlp_artifacts: NlpArtifacts = None) -> List[RecognizerResult]:
        """Análisis simplificado siguiendo el patrón del ID recognizer"""
        base_results = super().analyze(text, entities, nlp_artifacts)
        enhanced_results = []

        for result in base_results:
            detected_text = text[result.start:result.end]
            context = self._get_context(text, result.start, result.end)
            
            is_valid, loc_type, confidence = self._validate_location(detected_text, context)
            
            if is_valid:
                enhanced_results.append(RecognizerResult(
                    entity_type=self.ENTITY,
                    start=result.start,
                    end=result.end,
                    score=confidence
                ))

        return enhanced_results

    def get_supported_entities(self) -> List[str]:
        return [self.ENTITY]


def register_enhanced_recognizers(registry):
    """Registra el reconocedor siguiendo el mismo patrón"""
    try:
        recognizer = ColombianLocationRecognizer()
        registry.add_recognizer(recognizer)
        return True
    except Exception:
        return False