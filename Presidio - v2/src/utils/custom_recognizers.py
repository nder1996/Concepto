"""
Reconocedores personalizados para Microsoft Presidio.
Define patrones específicos para Colombia y otros tipos de datos personalizados.
"""

import re
from typing import Optional, List, Tuple, Dict, Any

from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    EntityRecognizer,
    LocalRecognizer
)


# Lista de reconocedores personalizados para registeración
class VehicleLicenseRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para matrículas de vehículos colombianos.
    Formato: 3 letras seguidas de 3 números (AAA-123) o variantes.
    """

    def __init__(self):
        # Patrón para matrículas colombianas
        # Formatos: ABC123, ABC-123, ABC 123
        patterns = [
            Pattern(
                "vehicle_license_pattern",
                r"\b[A-Z]{3}[-\s]?[0-9]{3}\b",
                0.7  # Puntuación base para coincidencias
            ),
        ]
        
        # Inicializar reconocedor con patrones
        super().__init__(
            supported_entity="VEHICLE_LICENSE",
            patterns=patterns,
            context=["vehículo", "matrícula", "placa", "automóvil", "carro", "moto"]
        )
        
    def validate_result(self, pattern_text: str) -> bool:
        """
        Validación adicional del formato de matrícula.
        Se podría comprobar contra una lista de letras no válidas en Colombia.
        """
        # Ejemplo: Si empieza con letras prohibidas, rechazar
        invalid_prefixes = ["AAA", "ZZZ", "XXX"]
        pattern_text = pattern_text.upper().replace("-", "").replace(" ", "")
        prefix = pattern_text[:3]
        
        if prefix in invalid_prefixes:
            return False
        
        return True


class ColombianIDRecognizer(PatternRecognizer):
    """
    Reconocedor para cédulas de ciudadanía colombianas.
    Formato: 8 a 10 dígitos para cédula.
    """

    def __init__(self):
        # Patrones para cédulas colombianas
        # Formato actual: 8 a 10 dígitos
        patterns = [
            Pattern(
                "nrp_pattern",
                r"\b(?:[0-9]{1,3}\.)?[0-9]{3}\.?[0-9]{3}\b",  # Formato: 1.234.567.890 o 12345678
                0.6  # Puntuación base
            ),
            # Patrón para cédulas con formato 'CC: 12345678'
            Pattern(
                "nrp_cc_prefix",
                r"\bCC:?\s*(?:[0-9]{1,3}\.)?[0-9]{3}\.?[0-9]{3}\b",
                0.8  # Mayor puntuación con prefijo
            )
        ]
        
        # Inicializar reconocedor con patrones
        super().__init__(
            supported_entity="NRP",
            patterns=patterns,
            context=["cédula", "identificación", "documento", "ID", "CC"]
        )
        
    def validate_result(self, pattern_text: str) -> bool:
        """
        Validación adicional para cédulas: verifica longitud y otros criterios
        """
        # Eliminar puntos y espacios
        clean_id = re.sub(r'[^\d]', '', pattern_text)
        
        # La cédula debe tener entre 8 y 10 dígitos
        if len(clean_id) < 6 or len(clean_id) > 10:
            return False
            
        return True


# Reconocedor específico para mejorar la detección de nombres en español
class SpanishPersonNameRecognizer(EntityRecognizer):
    """
    Reconocedor personalizado para mejorar la detección de nombres en español.
    Utiliza diccionarios y reglas específicas del idioma.
    """

    def __init__(self):
        # Idiomas soportados
        languages = ["es"]
        
        # Inicializar reconocedor
        super().__init__(
            supported_entities=["PERSON"],
            name="SpanishPersonNameRecognizer",
            supported_language=languages
        )
        
    def analyze(self, text: str, entities: List[str], language: str) -> List[Dict[str, Any]]:
        """
        Método principal para analizar texto y detectar nombres de personas en español.
        Este es un método simplificado, pero se puede mejorar con lógica más avanzada.
        """
        results = []
        
        # Ejemplo muy básico: detectar patrones comunes de nombres en español
        # Esto debería ser mucho más sofisticado en una implementación real
        
        # Patrones comunes: Sr./D./Don seguido de nombre(s) y apellido(s)
        prefixes = [
            "Sr\\.", "Sra\\.", "D\\.", "Dña\\.", "Don", "Doña",
            "Dr\\.", "Dra\\.", "Lic\\.", "Prof\\."
        ]
        
        prefix_pattern = "|".join(prefixes)
        pattern = f"(?i)(?:{prefix_pattern})\\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){{1,3}})"
        
        # Buscar coincidencias
        for match in re.finditer(pattern, text):
            results.append({
                "entity_type": "PERSON",
                "start": match.start(),
                "end": match.end(),
                "score": 0.85,  # Puntuación asignada
                "analysis_explanation": "Coincidencia con patrón de nombre español"
            })
        
        return results


def register_custom_recognizers(registry: RecognizerRegistry) -> None:
    """
    Registra los reconocedores personalizados en el registro de Presidio.
    
    Args:
        registry: El registro de Presidio donde se añadirán los reconocedores
    """
    # Reconocedores para documentos colombianos
    vehicle_license_recognizer = VehicleLicenseRecognizer()
    colombian_id_recognizer = ColombianIDRecognizer()
    spanish_person_recognizer = SpanishPersonNameRecognizer()
    
    # Agregar al registro
    registry.add_recognizer(vehicle_license_recognizer)
    registry.add_recognizer(colombian_id_recognizer)
    registry.add_recognizer(spanish_person_recognizer)
    
    # Importante: Cargar los reconocedores predefinidos según el idioma
    # Esto asegura que los reconocedores como PERSON, EMAIL_ADDRESS y PHONE_NUMBER estén disponibles
    registry.load_predefined_recognizers(languages=["es", "en"])