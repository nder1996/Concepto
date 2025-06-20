from presidio_analyzer import PatternRecognizer, Pattern

class ColombianPhoneRecognizer(PatternRecognizer):
    """
    Recognizer para números de teléfono móviles colombianos.
    Detecta secuencias de 10 dígitos que comienzan con 3.
    """
    PATTERNS = [
        Pattern(
            "Colombian mobile number",
            r"\b(?:\+57\s?)?3\d{9}\b",
            0.5  # Móviles (10 dígitos, opcional +57)
        ),
        Pattern(
            "Colombian landline number",
            r"\b(?:\+57\s?)?[1-7]\d{7}\b",
            0.5  # Fijos (código de ciudad + 7 dígitos, opcional +57)
        )
    ]

    def __init__(self, supported_language="es"):
        super().__init__(
            supported_entity="PHONE_NUMBER",
            supported_language=supported_language,
            patterns=self.PATTERNS,
        )
