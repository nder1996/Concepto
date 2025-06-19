from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts


class ColombianIDRecognizer(PatternRecognizer):
    """
    Reconocedor avanzado para documentos de identidad colombianos que:
    - Detecta CC, TI, PA, CE, RC, NIT, PEP y Visa
    - Analiza contexto (50 caracteres antes/después)
    - Identifica patrones como "mi cédula", "mi documento"
    - Valida formatos específicos para cada tipo
    """

    ENTITY = "COLOMBIAN_ID_DOC"

    # Configuración detallada para cada tipo de documento
    DOCUMENT_CONFIG = {        "CC": {
            "name": "Cédula de Ciudadanía",
            "regex": r"\b(?:c[eé]dula|cedula|c\.?\s*c\.?|c[eé]d\.?|ced\.?|documento|identificaci[oó]n|identidad|tarjeta\s+de\s+identidad)\b",
            "pattern": r"(?<!\w)(\d{6,12})(?!\w)",
            "context_keywords": [
                "cédula",
                "cedula",
                "cc",
                "c.c.",
                "c. c.",
                "ciudadanía",
                "ciudadania",
                "documento",
                "doc",
                "portador",
                "identificación",
                "identificacion",
                "identidad",
                "ced",
                "céd",
                "número",
                "numero",
                "no.",
                "#",
                "dni",
                "id",
                "personal",
                "nacional",
                "colombiano",
                "colombiana",
                "registraduría",
                "registraduria",
                "carnet",
                "carné",
                "tarjeta",
                "república",
                "republica",
                "expedida",
                "expedido",
                "vigente",
                "fecha",
                "nacimiento",
                "lugar",
                "expedición",
                "expedicion",
                "identificado",
                "identificada",
            ],
            "min_length": 5,  # Para capturar algunas cédulas antiguas o especiales
            "max_length": 15,  # Para capturar formatos con puntos, guiones, etc.
            "score": 0.8,  # Reducido para capturar más casos
        },        "TI": {
            "name": "Tarjeta de Identidad",
            "regex": r"\b(?:tarjeta\s+de\s+identidad|tarjeta\s+identidad|t\.?\s*i\.?|t\s+de\s+i|ti|identidad\s+(?:de\s+)?menor|documento\s+(?:de\s+)?menor|nuip)\b",
            "pattern": r"(?<!\w)(\d{8,12})(?!\w)",
            "context_keywords": [
                "tarjeta",
                "identidad",
                "ti",
                "t.i.",
                "t. i.",
                "t de i",
                "menor",
                "menor de edad",
                "joven",
                "adolescente",
                "niño",
                "niña",
                "juvenil",
                "nuip",
                "número único",
                "numero unico",
                "identificación",
                "identificacion",
                "documento",
                "registro",
                "civil",
                "registraduría",
                "registraduria",
                "república",
                "republica",
                "colombia",
                "colombiano",
                "colombiana",
                "expedida",
                "expedido",
                "vigente",
                "fecha",
                "nacimiento",
                "lugar",
                "expedición",
                "expedicion",
                "identificado",
                "identificada",
                "estudiante",
                "escolar",
                "colegio",
                "instituto",
                "bachiller",
            ],
            "min_length": 8,  # Las TI tienen mínimo 8 dígitos
            "max_length": 15,  # Para incluir formatos con puntos y guiones
            "score": 0.8,  # Reducido para capturar más casos
        },
        "PA": {
            "name": "Pasaporte",
            "regex": r"\b(?:pasaporte|pa\.?)\b",
            "pattern": r"(?<!\w)([A-Z]{1,2}\d{4,7})(?!\w)",
            "context_keywords": ["pasaporte", "pa", "internacional"],
            "min_length": 5,
            "max_length": 9,
            "score": 0.85,
        },
        "CE": {
            "name": "Cédula de Extranjería",
            "regex": r"\b(?:c[eé]dula\s*(?:de\s*extranjer[ií]a)?|c\.?e\.?)\b",
            "pattern": r"(?<!\d)([A-Z]?\d{5,8})(?!\d)",
            "context_keywords": ["extranjería", "ce", "extranjero"],
            "min_length": 5,
            "max_length": 8,
            "score": 0.85,
        },
        "RC": {
            "name": "Registro Civil",
            "regex": r"\b(?:registro\s*(?:civil)?|r\.?c\.?)\b",
            "pattern": r"(?<!\d)(\d{8,12})(?!\d)",
            "context_keywords": ["registro", "rc", "nacimiento"],
            "min_length": 8,
            "max_length": 12,
            "score": 0.85,
        },
        "NIT": {
            "name": "Número de Identificación Tributaria",
            "regex": r"\b(?:nit|n\.?i\.?t\.?)\b",
            "pattern": r"(?<!\d)(\d{9,11}(?:-?\d)?)(?!\d)",
            "context_keywords": ["nit", "tributario", "empresa"],
            "min_length": 9,
            "max_length": 12,
            "score": 0.95,
        },
        "PEP": {
            "name": "Permiso Especial de Permanencia",
            "regex": r"\b(?:pep|permiso\s*especial\s*de\s*permanencia)\b",
            "pattern": r"(?<!\w)([A-Z0-9]{5,15})(?!\w)",
            "context_keywords": ["pep", "permiso", "migración"],
            "min_length": 5,
            "max_length": 15,
            "score": 0.8,
        },
        "VISA": {
            "name": "Visa Colombiana",
            "regex": r"\b(?:visa|visado)\b",
            "pattern": r"(?<!\w)([A-Z0-9]{8,12})(?!\w)",
            "context_keywords": ["visa", "visado", "consulado"],
            "min_length": 8,
            "max_length": 12,
            "score": 0.8,
        },
    }

    # Expresiones posesivas para mejorar el contexto
    POSSESSIVE_PATTERNS = [
        (
            re.compile(
                r"\b(?:mi|su|este|mi\s*[a-z]+\s*)(cédula|documento|tarjeta|pasaporte|registro|nit|pep|visa)\b",
                re.IGNORECASE,
            ),
            0.3,
        ),
        (
            re.compile(
                r"\b(?:número|num|no\.?)\s*de\s*(cédula|documento|tarjeta|pasaporte|registro|nit|pep|visa)\b",
                re.IGNORECASE,
            ),
            0.25,
        ),
        (
            re.compile(
                r"\b(cédula|documento|tarjeta|pasaporte|registro|nit|pep|visa)\s*(?:es|del portador es|número|num|no\.?)\s*[:=]?\s*",
                re.IGNORECASE,
            ),
            0.3,
        ),
        (
            re.compile(
                r"\b(?:el|la|portador)\s+(?:es|tiene|con)\s+(?:número|num|no\.?)?\s*[:=]?\s*",
                re.IGNORECASE,
            ),
            0.3,
        ),
    ]

    def __init__(self):
        patterns = self._build_patterns()
        context = self._build_context_words()

        super().__init__(
            supported_entity=self.ENTITY,
            patterns=patterns,            context=context,
            supported_language="es",
            name="ColombianIDRecognizer",
        )

    def _build_patterns(self) -> List[Pattern]:
        """Construye los patrones de reconocimiento para cada tipo de documento"""
        patterns = []
        for doc_type, config in self.DOCUMENT_CONFIG.items():
            # 1. Patrón para "tipo de documento seguido de número"
            # Ejemplo: "cédula 12345678", "tarjeta de identidad 123456789"
            type_number_pattern = f"\\b{config['regex']}\\s*[:=]?\\s*{config['pattern']}"
            
            # 2. Patrón para "el/la documento es número"
            # Ejemplo: "la cédula es 12345678", "mi tarjeta de identidad es 123456789"
            document_is_pattern = f"\\b(?:mi|su|la|el|esta|este)\\s+{config['regex']}\\s+(?:es|número|num|no\\.?)\\s*[:=]?\\s*{config['pattern']}"
            
            # 3. Patrón para números que aparecen cerca de palabras clave (contexto)
            # Este patrón busca números que estén cerca de las palabras de contexto
            context_number_pattern = f"\\b{config['pattern']}\\b"

            patterns.append(
                Pattern(
                    name=f"col_{doc_type.lower()}_type_number",
                    regex=type_number_pattern,
                    score=config["score"],
                )
            )

            patterns.append(
                Pattern(
                    name=f"col_{doc_type.lower()}_document_is",
                    regex=document_is_pattern,
                    score=config["score"] + 0.1,  # Mayor confianza por estructura clara
                )
            )

            # Solo agregar patrón de contexto con score más bajo
            patterns.append(
                Pattern(
                    name=f"col_{doc_type.lower()}_context",
                    regex=context_number_pattern,
                    score=config["score"] - 0.3,  # Menor confianza, necesita validación de contexto
                )
            )
        return patterns

    def _build_context_words(self) -> List[str]:
        """Construye la lista de palabras de contexto para todos los documentos"""
        context_words = []
        for config in self.DOCUMENT_CONFIG.values():
            context_words.extend(config["context_keywords"])
        return list(set(context_words))  # Eliminar duplicados

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """Analiza el texto con contexto extendido y validación mejorada"""
        # Obtener resultados base
        base_results = super().analyze(text, entities, nlp_artifacts)
        enhanced_results = []

        for result in base_results:
            # Extraer contexto (50 caracteres antes/después)
            context_start = max(0, result.start - 50)
            context_end = min(len(text), result.end + 50)
            context_text = text[context_start:context_end]

            # Validar el documento en su contexto
            is_valid, doc_type, confidence = self._validate_with_context(
                text[result.start : result.end], context_text
            )

            if is_valid:
                # Crear resultado con tipo específico
                enhanced_results.append(
                    RecognizerResult(
                        entity_type=f"{self.ENTITY}_{doc_type}",
                        start=result.start,
                        end=result.end,
                        score=confidence,
                        analysis_explanation=result.analysis_explanation,
                    )                )

        return enhanced_results

    def _validate_with_context(
        self, doc_text: str, context_text: str
    ) -> Tuple[bool, str, float]:
        """Valida un documento con análisis de contexto simplificado"""
        # Normalizar textos para comparación
        doc_text = doc_text.strip()
        context_text = context_text.lower()

        # 1. Determinar tipo de documento buscando patrones conocidos
        doc_type = None
        best_confidence = 0.0
        
        for dtype, config in self.DOCUMENT_CONFIG.items():
            # Buscar coincidencia del tipo en el contexto
            if re.search(config["regex"], context_text, re.IGNORECASE):
                # Validar que el número tenga un formato básico apropiado
                if re.match(config["pattern"], doc_text, re.IGNORECASE):
                    # Validar longitud básica
                    if config["min_length"] <= len(doc_text) <= config["max_length"]:
                        current_confidence = config["score"]
                        
                        # Aumentar confianza si hay patrones posesivos
                        for pattern, boost in self.POSSESSIVE_PATTERNS:
                            if pattern.search(context_text):
                                current_confidence = min(1.0, current_confidence + boost)
                                break
                        
                        # Usar el tipo con mayor confianza
                        if current_confidence > best_confidence:
                            doc_type = dtype
                            best_confidence = current_confidence

        # Si no encontramos un tipo específico pero el número parece válido, usar CC como predeterminado
        if not doc_type:
            # Para números de 8-11 dígitos, asumir que es una cédula si hay contexto de identidad
            if re.match(r'\d{8,11}', doc_text) and any(word in context_text for word in ['identidad', 'documento', 'tarjeta', 'cédula', 'cedula']):
                doc_type = 'CC'
                best_confidence = 0.6  # Confianza moderada
            else:
                return False, "", 0.0

        return True, doc_type, best_confidence

    def get_supported_entities(self) -> List[str]:
        """Devuelve todas las entidades soportadas (tipos de documentos)"""
        return [f"{self.ENTITY}_{doc_type}" for doc_type in self.DOCUMENT_CONFIG.keys()]


def register_enhanced_recognizers(registry):
    """
    Registra un reconocedor de documentos colombianos mejorado en el registro de Presidio.

    Args:
        registry: El registro de Presidio donde se registrarán los reconocedores
    """
    try:
        # Crear y registrar el reconocedor de documentos colombianos
        colombian_id_recognizer = ColombianIDRecognizer()
        registry.add_recognizer(colombian_id_recognizer)
        return True
    except Exception as e:
        # No lanzar excepción aquí para evitar interrumpir el flujo completo
        # El sistema de registro ya maneja este error en registry.py
        return False
