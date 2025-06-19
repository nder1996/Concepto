from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts
from src.config.entity_config import DOCUMENT_SCORES
import logging


# Configurar el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Agregar un handler de consola
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class ColombianIDRecognizer(PatternRecognizer):
    """
    Reconocedor avanzado para documentos de identidad colombianos que:
    - Detecta CC, TI, PA, CE, RC, NIT, PEP y Visa
    - Analiza contexto (50 caracteres antes/después)
    - Identifica patrones como "mi cédula", "mi documento"
    - Valida formatos específicos para cada tipo
    """

    ENTITY = "COLOMBIAN_ID_DOC"
    SUPPORTED_LANGUAGE = "es"  # Configuración para idioma español

    # Lista de documentos habilitados ahora viene de las claves de DOCUMENT_SCORES
    ENABLED_DOCUMENTS = list(DOCUMENT_SCORES.keys())

    # Configuración detallada para cada tipo de documento
    _FULL_DOCUMENT_CONFIG = {
        "CC": {
            "name": "Cédula de Ciudadanía",
            "regex": r"\b(?:c[eé]dula|cedula|c\.?\s*c\.?\.?|c[eé]d\.?|ced\.?|documento|identificaci[oó]n)\b",
            "context_number_pattern": r"\b(?:c[eé]dula|cedula|c\.\?\s*c\.\?|c[eé]d\.\?|ced\.\?|documento|identificaci[oó]n)\b(?:\W+|\s+(?:es|número|numero|no\.\?|:|de|del|es|es el|es la|es número|es numero|es no\.\?|es:|es el número|es el numero|es el no\.\?|es el:|es la número|es la numero|es la no\.\?|es la:|es un|es una|es mi|es su|es tu|es nuestro|es vuestra|es su número|es su numero|es su no\.\?|es su:|es tu número|es tu numero|es tu no\.\?|es tu:|es nuestro número|es nuestro numero|es nuestro no\.\?|es nuestro:|es vuestra número|es vuestra numero|es vuestra no\.\?|es vuestra:|es:)\s*){0,5})(\d{6,12})(?!\w)",
            "pattern": r"(?<!\w)(\d{6,12})(?!\w)",
            "context_keywords": [
                "cédula",
                "cedula",
                "cédula de ciudadanía",
                "cedula de ciudadania",
                "cédula ciudadanía",
                "cedula ciudadania",
                "cc",
                "c.c.",
                "ciudadanía",
                "ciudadania",
                "documento",
                "doc",
                "portador",
                "identificación",
                "identificacion",
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
            "score": DOCUMENT_SCORES.get("CC", 0),
        },
        "TI": {
            "name": "Tarjeta de Identidad",
            "regex": r"\b(?:tarjeta\s+de\s+identidad|ti(?!\w))\b",
            "pattern": r"(?<!\w)(\d{8,12})(?!\w)",
            "context_keywords": ["tarjeta", "identidad", "ti"],
            "min_length": 8,  # Las TI tienen mínimo 8 dígitos
            "max_length": 15,  # Para incluir formatos con puntos y guiones
            "score": DOCUMENT_SCORES.get("TI", 0),
        },
        "PA": {
            "name": "Pasaporte",
            "regex": r"\b(?:pasaporte|pa\.?)\b",
            "pattern": r"(?<!\w)([A-Z]{1,2}\d{4,7})(?!\w)",
            "context_keywords": ["pasaporte", "pa", "internacional"],
            "min_length": 5,
            "max_length": 9,
            "score": DOCUMENT_SCORES.get("PA", 0),
        },
        "CE": {
            "name": "Cédula de Extranjería",
            "regex": r"\b(?:c[eé]dula\s*(?:de\s*extranjer[ií]a)?|c\.?e\.?)\b",
            "pattern": r"(?<!\d)([A-Z]?\d{5,8})(?!\d)",
            "context_keywords": ["extranjería", "ce", "extranjero"],
            "min_length": 5,
            "max_length": 8,
            "score": DOCUMENT_SCORES.get("CE", 0),
        },
        "RC": {
            "name": "Registro Civil",
            "regex": r"\b(?:registro\s*(?:civil)?|r\.?c\.?)\b",
            "pattern": r"(?<!\d)(\d{8,12})(?!\d)",
            "context_keywords": ["registro", "rc", "nacimiento"],
            "min_length": 8,
            "max_length": 12,
            "score": DOCUMENT_SCORES.get("RC", 0),
        },
        "NIT": {
            "name": "Número de Identificación Tributaria",
            "regex": r"\b(?:nit|n\.?i\.?t\.?)\b",
            "pattern": r"(?<!\d)(\d{9,11}(?:-?\d)?)(?!\d)",
            "context_keywords": ["nit", "tributario", "empresa"],
            "min_length": 9,
            "max_length": 12,
            "score": DOCUMENT_SCORES.get("NIT", 0),
        },
        "PEP": {
            "name": "Permiso Especial de Permanencia",
            "regex": r"\b(?:pep|permiso\s*especial\s*de\s*permanencia)\b",
            "pattern": r"(?<!\w)([A-Z0-9]{5,15})(?!\w)",
            "context_keywords": ["pep", "permiso", "migración"],
            "min_length": 5,
            "max_length": 15,
            "score": DOCUMENT_SCORES.get("PEP", 0),
        },
        "VISA": {
            "name": "Visa Colombiana",
            "regex": r"\b(?:visa|visado)\b",
            "pattern": r"(?<!\w)([A-Z0-9]{8,12})(?!\w)",
            "context_keywords": ["visa", "visado", "consulado"],
            "min_length": 8,
            "max_length": 12,
            "score": DOCUMENT_SCORES.get("VISA", 0),
        },
    }

    @classmethod
    def get_active_document_config(cls):
        """
        Retorna solo la configuración de los documentos activos según DOCUMENT_SCORES.
        """
        return {k: v for k, v in cls._FULL_DOCUMENT_CONFIG.items() if k in DOCUMENT_SCORES}
    
    def __init__(self):
        self.name = "Colombian ID Recognizer"
        self.supported_language = "es"
        self.is_loaded = True
        patterns = self._build_patterns()
        if not patterns:
            logger.error("No se encontraron patrones válidos para los documentos activos en DOCUMENT_SCORES.")
            raise ValueError("ColombianIDRecognizer debe inicializarse con al menos un patrón válido.")
        super().__init__(supported_entity=self.ENTITY, patterns=patterns)
        self.active_document_config = self.get_active_document_config()
        self.supported_entity = self.ENTITY  # Agregar atributo para compatibilidad con Presidio

    # Solo incluir los documentos activos en DOCUMENT_SCORES
    DOCUMENT_CONFIG = {k: v for k, v in _FULL_DOCUMENT_CONFIG.items() if k in list(DOCUMENT_SCORES.keys())}

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

    def _build_patterns(self) -> List[Pattern]:
        """Construye los patrones de reconocimiento para cada tipo de documento"""
        patterns = []
        for doc_type, config in self.DOCUMENT_CONFIG.items():
            if doc_type not in self.ENABLED_DOCUMENTS:
                continue
            # 1. Patrón para "tipo de documento seguido de número"
            # Ejemplo: "cédula 12345678", "tarjeta de identidad 123456789"
            type_number_pattern = (
                f"\\b{config['regex']}\\s*[:=]?\\s*{config['pattern']}"
            )

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
                    score=config["score"]
                    - 0.3,  # Menor confianza, necesita validación de contexto
                )
            )
        return patterns

    def _build_context_words(self) -> List[str]:
        """Construye la lista de palabras de contexto para todos los documentos habilitados"""
        context_words = []
        for doc_type, config in self.DOCUMENT_CONFIG.items():
            if doc_type not in self.ENABLED_DOCUMENTS:
                continue
            context_words.extend(config["context_keywords"])
        return list(set(context_words))  # Eliminar duplicados

    def _is_phone_number(self, text: str) -> bool:
        """
        Detecta si el texto tiene formato de número telefónico colombiano.
        Solo detecta celulares (3xxxxxxxxx, +573xxxxxxxx, 573xxxxxxxx, 00573xxxxxxxx) y fijos de Bogotá (7 dígitos o 1xxxxxxx).
        No intenta cubrir todos los casos de fijos nacionales para evitar falsos positivos.
        """
        clean_text = re.sub(r'[\s\-\.\(\)]', '', text)
        # Celulares
        if re.fullmatch(r"(\+57|57|0057)?3\d{9}", clean_text):
            return True
        # Fijo Bogotá (7 dígitos o 1xxxxxxx)
        if re.fullmatch(r"(\+57|57|0057)?1\d{7}", clean_text):
            return True
        # Solo 7 dígitos (posible fijo Bogotá)
        if re.fullmatch(r"\d{7}", clean_text):
            return True
        return False

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """Analiza el texto con contexto extendido y validación mejorada"""
        logger.debug(f"Texto recibido para análisis: {text}")
        logger.debug(f"Entidades solicitadas: {entities}")
        base_results = super().analyze(text, entities, nlp_artifacts)
        logger.debug(f"Resultados base detectados: {base_results}")
        
        enhanced_results = []

        for result in base_results:
            detected_text = text[result.start : result.end]
            logger.debug(f"Texto detectado: {detected_text}, Score: {result.score}")
            # Evitar etiquetas tipo <...>
            if detected_text.startswith("<") and detected_text.endswith(">"):
                continue
            # Evitar palabras de contexto sin número
            if detected_text.lower() in [
                "identificado",
                "identificada",
                "identificacion",
                "identificación",
                "documento",
                "tarjeta",
                "cédula",
                "cedula",
                "registro",
                "pep",
                "visa",
                "pasaporte",
                "civil",
                "nit",
                "estudiante",
            ]:
                continue
            # --- NUEVO: Si el texto es un teléfono, omitirlo ---
            #if self._is_phone_number(detected_text):
            #    continue
            # Extraer contexto (50 caracteres antes/después)
            context_start = max(0, result.start - 50)
            context_end = min(len(text), result.end + 50)
            context_text = text[context_start:context_end].lower()
            # Solo anonimizar si en el contexto hay un número de al menos 5 dígitos
            if not re.search(r"\d{5,}", context_text):
                continue
            # Validar el documento en su contexto
            is_valid, doc_type, confidence = self._validate_with_context(
                text[result.start : result.end], context_text
            )
            if is_valid:
                enhanced_results.append(
                    RecognizerResult(
                        entity_type=self.ENTITY,  # Usar solo la entidad base
                        start=result.start,
                        end=result.end,
                        score=confidence,
                        analysis_explanation=result.analysis_explanation,
                    )
                )
        return enhanced_results

    def _validate_with_context(
        self, doc_text: str, context_text: str
    ) -> Tuple[bool, str, float]:
        """Valida un documento con análisis de contexto mejorado para todos los tipos habilitados
        Ahora es más permisivo: si el patrón y la longitud son correctos, acepta aunque el contexto no sea perfecto."""
        # Normalizar textos para comparación
        doc_text = doc_text.strip()
        context_text = context_text.lower()

        # Lista de candidatos posibles (tipo, confianza)
        candidates = []

        # 1. Buscar coincidencias por regex de contexto Y patrón de formato
        for dtype, config in self.DOCUMENT_CONFIG.items():
            if dtype not in self.ENABLED_DOCUMENTS:
                continue
            current_confidence = 0.0

            # Permitir frases como "su cédula de ciudadanía es" como contexto válido
            if re.search(r"(mi|su|la|el|esta|este)\s+c[eé]dula(\s+de\s+ciudadan[ií]a)?\s+es", context_text):
                if re.search(config["pattern"], doc_text, re.IGNORECASE) and config["min_length"] <= len(doc_text) <= config["max_length"]:
                    candidates.append((dtype, 0.95))
                    continue

            # --- MEJORA: Si el contexto contiene exactamente 'tarjeta de identidad' antes del número, priorizar TI ---
            if dtype == "TI":
                ti_context_patterns = [
                    r"tarjeta\s+de\s+identidad\s*[:=]?\s*" + config["pattern"],
                    r"mi\s+tarjeta\s+de\s+identidad\s*[:=]?\s*" + config["pattern"],
                ]
                for ti_pat in ti_context_patterns:
                    if re.search(ti_pat, context_text + " " + doc_text, re.IGNORECASE):
                        return True, "TI", 0.98

            # Verificar si el contexto menciona este tipo de documento
            context_match = re.search(config["regex"], context_text, re.IGNORECASE)

            # Verificar si el texto coincide con el patrón del documento
            pattern_match = re.search(config["pattern"], doc_text, re.IGNORECASE)

            # Verificar longitud
            length_valid = config["min_length"] <= len(doc_text) <= config["max_length"]

            if pattern_match and length_valid:
                # Si el contexto es bueno, score normal
                if context_match:
                    current_confidence = config["score"]
                else:
                    # Si el contexto no es perfecto pero el patrón y longitud sí, score aceptable
                    current_confidence = config["score"] * 0.85
                # Aumentar confianza si hay patrones posesivos
                for pattern, boost in self.POSSESSIVE_PATTERNS:
                    if pattern.search(context_text):
                        current_confidence = min(1.0, current_confidence + boost)
                        break
                candidates.append((dtype, current_confidence))

        # 2. Si no hay coincidencias por regex, buscar por palabras clave en contexto
        if not candidates:
            for dtype, config in self.DOCUMENT_CONFIG.items():
                if dtype not in self.ENABLED_DOCUMENTS:
                    continue
                # Contar coincidencias de palabras clave
                keyword_matches = sum(
                    1
                    for keyword in config["context_keywords"]
                    if keyword.lower() in context_text
                )

                if keyword_matches > 0:
                    # Verificar patrón y longitud
                    pattern_match = re.search(
                        config["pattern"], doc_text, re.IGNORECASE
                    )
                    length_valid = (
                        config["min_length"] <= len(doc_text) <= config["max_length"]
                    )

                    if pattern_match and length_valid:
                        # Calcular confianza basada en palabras clave encontradas
                        keyword_confidence = min(0.8, keyword_matches * 0.2)
                        base_confidence = (
                            config["score"] * 0.7
                        )  # Reducir confianza base
                        current_confidence = min(
                            0.9, base_confidence + keyword_confidence
                        )

                        candidates.append((dtype, current_confidence))

        # 3. Validación por formato específico sin contexto claro
        if not candidates:
            for dtype, config in self.DOCUMENT_CONFIG.items():
                if dtype not in self.ENABLED_DOCUMENTS:
                    continue
                pattern_match = re.search(config["pattern"], doc_text, re.IGNORECASE)
                length_valid = (
                    config["min_length"] <= len(doc_text) <= config["max_length"]
                )

                if pattern_match and length_valid:
                    # Confianza baja pero válida
                    current_confidence = config["score"] * 0.4

                    # Casos especiales por formato
                    if dtype == "NIT" and re.match(r"\d{9,11}-?\d?", doc_text):
                        current_confidence = 0.7  # NITs tienen formato muy específico
                    elif dtype == "PA" and re.match(r"[A-Z]{1,2}\d{4,7}", doc_text):
                        current_confidence = 0.7  # Pasaportes tienen formato distintivo
                    elif dtype == "CE" and re.match(r"[A-Z]?\d{5,8}", doc_text):
                        current_confidence = 0.6  # CE puede tener letra inicial
                    elif dtype == "PEP" and re.match(r"[A-Z0-9]{8,15}", doc_text):
                        current_confidence = 0.6  # PEP formato alfanumérico
                    elif dtype == "VISA" and re.match(r"[A-Z0-9]{8,12}", doc_text):
                        current_confidence = 0.6  # VISA formato alfanumérico

                    candidates.append(
                        (dtype, current_confidence)
                    )  # 4. Fallback inteligente para números puros (CC, TI, RC)
        if not candidates and re.match(r"\d+", doc_text):
            doc_length = len(doc_text)

            # Verificación específica para T.I con patrones flexibles
            ti_patterns = [
                r"\bt\.?\s*i\.?\s*\b",
                r"\bt\s*i\s*\b",
                r"\bti\b",
                r"\bt\s+de\s+i\b",
            ]

            for pattern in ti_patterns:
                if re.search(pattern, context_text, re.IGNORECASE):
                    if 8 <= doc_length <= 12:
                        candidates.append(("TI", 0.8))
                        break

            # Contextual clues para determinar el tipo más probable
            if not candidates:
                if any(
                    word in context_text
                    for word in ["menor", "niño", "niña", "adolescente", "estudiante"]
                ):
                    if 8 <= doc_length <= 12:
                        candidates.append(("TI", 0.6))
                elif any(
                    word in context_text for word in ["nacimiento", "civil", "registro"]
                ):
                    if 8 <= doc_length <= 12:
                        candidates.append(("RC", 0.6))
                elif any(
                    word in context_text
                    for word in ["empresa", "tributario", "fiscal", "rut"]
                ):
                    if 9 <= doc_length <= 12:
                        candidates.append(("NIT", 0.7))
                # Fallback general para cédula
                elif any(
                    word in context_text
                    for word in ["documento", "cédula", "cedula", "identificación"]
                ):
                    if 6 <= doc_length <= 12:
                        candidates.append(("CC", 0.4))

        # Seleccionar el candidato con mayor confianza
        if candidates:
            doc_type, best_confidence = max(candidates, key=lambda x: x[1])
            return True, doc_type, best_confidence

        return False, "", 0.0

    def get_supported_entities(self) -> List[str]:
        """Devuelve la entidad principal soportada"""
        return [self.ENTITY]


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
