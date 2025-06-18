# location_recognizer.py
# Reconocedor personalizado de ubicaciones para Colombia utilizando la librería py-countries-states-cities-database
from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult, RecognizerRegistry
import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts
import importlib.util

# Configuración de logging
logger = logging.getLogger(__name__)

# Definir variables para funciones que importaremos
csc_available = False
get_cities_for_country = None
get_states_for_country = None

# Intentamos importar py-countries-states-cities-database
try:
    # Importar correctamente según la documentación
    from py_countries_states_cities_database import (
        get_all_countries,
        get_all_states,
        get_all_cities,
        get_all_countries_and_states_nested,
        get_all_countries_and_cities_nested
    )
    csc_available = True
    logger.info("Biblioteca py-countries-states-cities-database cargada correctamente")
    
    # Definir funciones auxiliares para obtener ciudades y estados de un país específico
    def get_cities_for_country(country_code):
        """Obtiene todas las ciudades de un país específico."""
        all_cities = get_all_cities()
        return [city for city in all_cities if city.get('country_code') == country_code]
    
    def get_states_for_country(country_code):
        """Obtiene todos los estados/departamentos de un país específico."""
        all_states = get_all_states()
        return [state for state in all_states if state.get('country_code') == country_code]
    
    # Podemos usar también la función anidada para obtener estados y ciudades
    # Si es más eficiente para el caso de uso
    def get_country_data(country_code):
        """Obtiene los datos de un país específico."""
        countries_and_states = get_all_countries_and_states_nested()
        # Encontrar el país específico
        for country in countries_and_states:
            if country.get('iso2') == country_code or country.get('iso3') == country_code:
                return country
        return None
        
except ImportError as e:
    logger.error(f"Error al importar py-countries-states-cities-database: {e}")
    logger.warning("Por favor, instala la librería con: pip install py-countries-states-cities-database")
    # No elevamos la excepción para permitir que la aplicación continúe funcionando

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
            logger.warning("py-countries-states-cities-database no está disponible. El reconocedor funcionará con capacidades limitadas.")
            # No lanzamos error para permitir que la aplicación siga funcionando
            self.colombian_cities = []
        else:
            self.colombian_cities = self._get_colombian_locations()
        
        # Crear el patrón de ciudades, si tenemos ciudades disponibles
        if self.colombian_cities:
            cities_regex = r"""
                (?i)\b(?:{cities})\b
            """.format(cities="|".join(self.colombian_cities))
        else:
            # Patrón genérico para ciudades si no tenemos la lista
            cities_regex = r"""
                (?i)\b(?:bogot[aá]|medell[ií]n|cali|barranquilla|cartagena|c[uú]cuta|soledad|ibagu[eé]|bucaramanga|soacha|santa\s+marta|villavicencio|bello|pereira|valledupar|manizales|monter[ií]a|pasto|buenaventura|neiva|palmira|armenia|popay[aá]n|sincelejo|itag[uü][ií]|floridablanca|envigado|tulu[aá]|dosquebradas|tum|tunja|gir[oó]n|apartad[oó]|florencia|uribia|ipiales|turbo|maicao|piedecuesta)\b
            """
        
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
        if not csc_available:
            logger.warning("No se pueden obtener ubicaciones colombianas: biblioteca no disponible")
            return []
            
        try:
            # Obtener ciudades y estados de Colombia (código CO)
            cities = []
            if get_cities_for_country:
                cities_data = get_cities_for_country('CO')
                cities = [city['name'] for city in cities_data if 'name' in city]
            
            states = []
            if get_states_for_country:
                states_data = get_states_for_country('CO')
                states = [state['name'] for state in states_data if 'name' in state]
            
            # Si tenemos la función anidada, también podemos usarla
            if not cities and not states and 'get_country_data' in globals():
                country_data = get_country_data('CO')
                if country_data and 'states' in country_data:
                    states = [state['name'] for state in country_data['states'] if 'name' in state]
                    # Intentar extraer ciudades de los estados
                    for state in country_data.get('states', []):
                        if 'cities' in state:
                            cities.extend([city['name'] for city in state['cities'] if 'name' in city])
                
            all_locations = list(set(cities + states))
            
            if not all_locations:
                logger.warning("No se encontraron datos de ubicaciones colombianas en la base de datos.")
                # Usar lista de respaldo
                all_locations = [
                    "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", 
                    "Cundinamarca", "Antioquia", "Valle del Cauca", "Atlántico", "Bolívar",
                    "Boyacá", "Caldas", "Córdoba", "Magdalena", "Nariño", "Santander"
                ]
                
            return all_locations
        except Exception as e:
            logger.error(f"Error al obtener ubicaciones colombianas: {e}")
            return []
        
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
        
        if csc_available and get_cities_for_country and get_states_for_country:
            try:
                # Obtener ciudades y estados de Colombia
                states_data = get_states_for_country('CO')
                cities_data = get_cities_for_country('CO')
                
                # Verificamos si es un departamento (estado) o ciudad
                pattern_words = pattern_text.split()
                for word in pattern_words:
                    if len(word) > 3:  # Evitar palabras muy cortas
                        # Buscar en estados (departamentos)
                        dept_match = any(word in state['name'].lower() for state in states_data if 'name' in state)
                        if dept_match:
                            is_location = True
                            break
                            
                        # Buscar en ciudades (municipios)
                        city_match = any(word in city['name'].lower() for city in cities_data if 'name' in city)
                        if city_match:
                            is_location = True
                            break
            except Exception as e:
                logger.error(f"Error al validar ubicación: {e}")
        else:
            # Si no tenemos la biblioteca, hacemos una comprobación básica con ciudades principales
            common_cities = ['bogota', 'medellin', 'cali', 'barranquilla', 'cartagena', 'cucuta', 
                            'ibague', 'bucaramanga', 'soacha', 'santa marta', 'villavicencio', 'pereira']
            common_departments = ['antioquia', 'atlantico', 'bolivar', 'boyaca', 'caldas', 'cundinamarca', 
                                'valle', 'santander', 'tolima', 'huila', 'cauca', 'narino']
            
            pattern_words = pattern_text.split()
            for word in pattern_words:
                if word in common_cities or word in common_departments:
                    is_location = True
                    break
        
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
            cities_data = get_cities_for_country('CO') if get_cities_for_country else []
            found_cities = []
            
            for city in cities_data:
                if 'name' in city and query_value_lower in city['name'].lower():
                    # Buscar el estado al que pertenece la ciudad
                    state_code = city.get('state_code', '')
                    states_data = get_states_for_country('CO') if get_states_for_country else []
                    state_name = next((state.get('name', "Desconocido") for state in states_data 
                                     if 'state_code' in state and state['state_code'] == state_code), "Desconocido")
                    
                    found_cities.append({
                        'code': city.get('id', ''),  # ID de la ciudad
                        'municipality': city.get('name', ''),
                        'department': state_name
                    })
            
            return found_cities if found_cities else None
            
        elif query_type == 'department':
            # Buscar departamento/estado por nombre (aproximado)
            query_value_lower = query_value.lower()
            states_data = get_states_for_country('CO') if get_states_for_country else []
            found_states = [
                {
                    'code': state.get('id', ''),  # ID del estado/departamento
                    'department': state.get('name', '')
                }
                for state in states_data if 'name' in state and query_value_lower in state['name'].lower()
            ]
            return found_states if found_states else None
            
        elif query_type == 'code':
            # Buscar por código (ID)
            # Nota: La biblioteca usa IDs diferentes al DANE, por lo que esto es una aproximación
            try:
                code_id = query_value  # Puede ser string o int
                # Buscar en estados
                states_data = get_states_for_country('CO') if get_states_for_country else []
                for state in states_data:
                    if str(state.get('id', '')) == str(code_id):
                        return {'code': state.get('id', ''), 'department': state.get('name', '')}
                
                # Buscar en ciudades
                cities_data = get_cities_for_country('CO') if get_cities_for_country else []
                for city in cities_data:
                    if str(city.get('id', '')) == str(code_id):
                        # Buscar el estado al que pertenece la ciudad
                        state_code = city.get('state_code', '')
                        states_data = get_states_for_country('CO') if get_states_for_country else []
                        state_name = next((state.get('name', "Desconocido") for state in states_data 
                                         if 'state_code' in state and state['state_code'] == state_code), "Desconocido")
                        
                        return {
                            'code': city.get('id', ''),
                            'municipality': city.get('name', ''),
                            'department': state_name
                        }
            except ValueError as e:
                logger.error(f"Error con el código proporcionado: {e}")
        
        return None
    except Exception as e:
        logger.error(f"Error consultando datos de ubicaciones: {str(e)}")
        return None