# location_recognizer.py
# Reconocedor personalizado de ubicaciones para Colombia utilizando la librería py-countries-states-cities-database
from presidio_analyzer import PatternRecognizer, Pattern
import re
import logging

# Configuración de logging
logger = logging.getLogger(__name__)

# Intentamos importar py-countries-states-cities-database
try:
    from pycountries_statescities.db import get_cities_by_country, get_states_by_country
    csc_available = True
except ImportError as e:
    logger.error(f"Error al importar py-countries-states-cities-database: {e}")
    csc_available = False
    raise ImportError("Por favor, instala la librería 'py-countries-states-cities-database'")

# Patrones para direcciones y lugares en Colombia
DIRECCION_REGEX = r"""
    (?i)\b(?:calle|cra|carrera|av|avenida|transversal|tv|diagonal|dg|manzana|mz|barrio|vereda|sector|parque|centro comercial|hospital|universidad|aeropuerto|terminal)\s*\d+[a-zA-Z]?\s*(?:#|nro\.?|num\.?|numero)?\s*\d+[a-zA-Z]?(?:\s*-\s*\d+)?\b
"""

# Patrones para conjunciones/preposiciones comunes en ubicaciones
CONJUNCIONES_REGEX = r"""
    (?i)\b(?:en|cerca de|entre|esquina con|al lado de|frente a|junto a|sobre|por|hacia|hasta|desde|a la altura de)\b
"""

# Patrón para códigos postales colombianos
POSTAL_CODE_REGEX = r"""
    (?i)\b\d{6}\b(?=.*(?:Colombia|Colombiano|Colombiana))
"""

class ColombianLocationRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado de ubicaciones para Colombia utilizando py-countries-states-cities-database.
    Detecta direcciones, ciudades, departamentos, municipios y otros lugares relevantes.
    """
    def __init__(self, supported_language="es"):
        if not csc_available:
            raise ImportError("py-countries-states-cities-database no está disponible. Por favor, instálala correctamente.")
        self.colombian_cities = self._get_colombian_locations()
        cities_regex = r"""
            (?i)\b(?:{cities})\b
        """.format(cities="|".join(self.colombian_cities))
        location_patterns = [
            Pattern("colombian_address", DIRECCION_REGEX, 0.7),
            Pattern("colombian_city", cities_regex, 0.8),
            Pattern("colombian_conjunction", CONJUNCIONES_REGEX, 0.5),
            Pattern("colombian_postal_code", POSTAL_CODE_REGEX, 0.6)
        ]
        super().__init__(
            supported_entity="COLOMBIAN_LOCATION",
            patterns=location_patterns,
            supported_language=supported_language,
            name="Colombian Location Recognizer"
        )

    def _get_colombian_locations(self):
        """
        Obtiene dinámicamente todas las entidades territoriales colombianas usando py-countries-states-cities-database.
        Returns:
            list: Lista de nombres de entidades territoriales.
        """
        # Obtener ciudades y estados de Colombia (código CO)
        cities = [city['name'] for city in get_cities_by_country('CO')]
        states = [state['name'] for state in get_states_by_country('CO')]
        all_locations = list(set(cities + states))
        if not all_locations:
            logger.warning("No se encontraron datos de ubicaciones colombianas en la base de datos.")
        return all_locations
        
    def validate_result(self, pattern_text):
        """
        Método para validar si el texto encontrado es realmente una ubicación colombiana.
        Utiliza la librería py-countries-states-cities-database para validar las ubicaciones.
        
        Args:
            pattern_text (str): El texto que coincide con el patrón.
            
        Returns:
            bool: True si el texto es una ubicación válida, False en caso contrario.
        """
        pattern_text = pattern_text.lower()
        
        # Palabras que pueden indicar falsos positivos
        false_positive_words = ['usuario', 'nombre', 'apellido', 'persona', 'empresa']
        
        # Verifica si es una dirección
        is_address = any(word in pattern_text for word in ['calle', 'carrera', 'avenida', 'diagonal', 'transversal', 'manzana', 'barrio'])
        
        # Verifica si coincide con una ciudad o departamento
        is_location = False
        
        try:
            # Obtener ciudades y estados de Colombia
            states = get_states_by_country('CO')
            cities = get_cities_by_country('CO')
            
            # Verificamos si es un departamento (estado) o ciudad
            pattern_words = pattern_text.split()
            for word in pattern_words:
                if len(word) > 3:  # Evitar palabras muy cortas
                    # Buscar en estados (departamentos)
                    dept_match = any(word in state['name'].lower() for state in states)
                    if dept_match:
                        is_location = True
                        break
                        
                    # Buscar en ciudades (municipios)
                    city_match = any(word in city['name'].lower() for city in cities)
                    if city_match:
                        is_location = True
                        break
        except Exception as e:
            logger.error(f"Error al validar ubicación: {e}")
        
        # Verificar si es un falso positivo
        is_false_positive = any(word in pattern_text for word in false_positive_words)
        
        # Devolver True si parece una ubicación y no un falso positivo
        return (is_address or is_location) and not is_false_positive

    def analyze(self, text, entities, nlp_artifacts=None):
        """
        Sobrescribe el método analyze para realizar validaciones adicionales
        
        Args:
            text (str): El texto a analizar.
            entities (list): Lista de entidades a buscar.
            nlp_artifacts: Artefactos NLP adicionales.
            
        Returns:
            List[RecognizerResult]: Lista de resultados del reconocedor.
        """
        # Llamar al método analyze de la clase padre
        results = super().analyze(text, entities, nlp_artifacts)
        
        # Filtrar resultados usando validate_result
        validated_results = [result for result in results if self.validate_result(text[result.start:result.end])]
        
        return validated_results

def query_location_data(query_type, query_value):
    """
    Consulta datos específicos de la división político-administrativa de Colombia usando py-countries-states-cities-database.
    
    Args:
        query_type (str): 'municipality' (ciudad), 'department' (estado/departamento), 'code' (no soportado completamente).
        query_value (str): Valor a consultar (nombre).
        
    Returns:
        dict: Información encontrada o None si no se encuentra.
    """
    if not csc_available:
        logger.error("py-countries-states-cities-database no está disponible para realizar consultas.")
        return None
    
    try:
        if query_type == 'municipality':
            # Buscar ciudad por nombre (aproximado)
            query_value_lower = query_value.lower()
            cities = get_cities_by_country('CO')
            found_cities = []
            
            for city in cities:
                if query_value_lower in city['name'].lower():
                    # Buscar el estado al que pertenece la ciudad
                    state_code = city['state_code']
                    states = get_states_by_country('CO')
                    state_name = next((state['name'] for state in states if state['state_code'] == state_code), "Desconocido")
                    
                    found_cities.append({
                        'code': city['id'],  # ID de la ciudad
                        'municipality': city['name'],
                        'department': state_name
                    })
            
            return found_cities if found_cities else None
            
        elif query_type == 'department':
            # Buscar departamento/estado por nombre (aproximado)
            query_value_lower = query_value.lower()
            states = get_states_by_country('CO')
            found_states = [
                {
                    'code': state['id'],  # ID del estado/departamento
                    'department': state['name']
                }
                for state in states if query_value_lower in state['name'].lower()
            ]
            return found_states if found_states else None
            
        elif query_type == 'code':
            # Buscar por código (ID)
            # Nota: La biblioteca usa IDs diferentes al DANE, por lo que esto es una aproximación
            try:
                code_id = int(query_value)
                # Buscar en estados
                states = get_states_by_country('CO')
                for state in states:
                    if state['id'] == code_id:
                        return {'code': state['id'], 'department': state['name']}
                
                # Buscar en ciudades
                cities = get_cities_by_country('CO')
                for city in cities:
                    if city['id'] == code_id:
                        # Buscar el estado al que pertenece la ciudad
                        state_code = city['state_code']
                        states = get_states_by_country('CO')
                        state_name = next((state['name'] for state in states if state['state_code'] == state_code), "Desconocido")
                        
                        return {
                            'code': city['id'],
                            'municipality': city['name'],
                            'department': state_name
                        }
            except ValueError:
                logger.error(f"Código proporcionado no es un número válido: {query_value}")
        
        return None
    except Exception as e:
        logger.error(f"Error consultando datos de ubicaciones: {str(e)}")
        return None

# Ejemplo de uso:
# from presidio_analyzer import AnalyzerEngine
# analyzer = AnalyzerEngine()
# analyzer.registry.add_recognizer(ColombianLocationRecognizer())
# info = query_location_data('municipality', 'Bogotá')
# print(info)