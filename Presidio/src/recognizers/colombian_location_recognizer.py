# colombian_location_recognizer.py
# Reconocedor personalizado de ubicaciones para Colombia utilizando la librería py-countries-states-cities-database
from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
import logging
from typing import List, Optional, Dict, Any
from presidio_analyzer.nlp_engine import NlpArtifacts

# Configuración de logging
logger = logging.getLogger(__name__)

# Definir variables para la biblioteca de ciudades/estados
class CSCDatabaseWrapper:
    """Wrapper para py-countries-states-cities-database para gestionar dependencias de forma limpia."""
    
    def __init__(self):
        self.available = False
        self.cities_cache = {}
        self.states_cache = {}
        self._initialize()
    
    def _initialize(self):
        """Inicializa el wrapper intentando cargar la biblioteca."""
        try:
            # Importar correctamente según la documentación
            from py_countries_states_cities_database import (
                get_all_countries,
                get_all_states,
                get_all_cities,
                get_all_countries_and_states_nested,
                get_all_countries_and_cities_nested
            )
            
            # Asignar las funciones al contexto de la clase
            self.get_all_countries = get_all_countries
            self.get_all_states = get_all_states
            self.get_all_cities = get_all_cities
            self.get_all_countries_and_states_nested = get_all_countries_and_states_nested
            self.get_all_countries_and_cities_nested = get_all_countries_and_cities_nested
            
            self.available = True
            logger.info("Biblioteca py-countries-states-cities-database cargada correctamente")
        except ImportError as e:
            logger.error(f"Error al importar py-countries-states-cities-database: {e}")
            logger.warning("Por favor, instala la librería con: pip install py-countries-states-cities-database")
            # No elevamos la excepción para permitir que la aplicación continúe funcionando
    
    def get_cities_for_country(self, country_code):
        """Obtiene todas las ciudades de un país específico con caché."""
        if not self.available:
            return []
            
        if country_code in self.cities_cache:
            return self.cities_cache[country_code]
            
        try:
            all_cities = self.get_all_cities()
            cities = [city for city in all_cities if city.get('country_code') == country_code]
            self.cities_cache[country_code] = cities
            return cities
        except Exception as e:
            logger.error(f"Error obteniendo ciudades para {country_code}: {e}")
            return []
    
    def get_states_for_country(self, country_code):
        """Obtiene todos los estados/departamentos de un país específico con caché."""
        if not self.available:
            return []
            
        if country_code in self.states_cache:
            return self.states_cache[country_code]
            
        try:
            all_states = self.get_all_states()
            states = [state for state in all_states if state.get('country_code') == country_code]
            self.states_cache[country_code] = states
            return states
        except Exception as e:
            logger.error(f"Error obteniendo estados para {country_code}: {e}")
            return []
    
    def get_country_data(self, country_code):
        """Obtiene los datos completos de un país específico."""
        if not self.available:
            return None
            
        try:
            countries_and_states = self.get_all_countries_and_states_nested()
            # Encontrar el país específico
            for country in countries_and_states:
                if country.get('iso2') == country_code or country.get('iso3') == country_code:
                    return country
            return None
        except Exception as e:
            logger.error(f"Error obteniendo datos para país {country_code}: {e}")
            return None

# Crear la instancia global
csc_db = CSCDatabaseWrapper()

# Patrones para direcciones y lugares en Colombia
DIRECCION_REGEX = r"(?i)\b(?:calle|cra|carrera|av|avenida|transversal|tv|diagonal|dg|manzana|mz|barrio|vereda|sector|parque|centro comercial|hospital|universidad|aeropuerto|terminal)\s*\d+[a-zA-Z]?\s*(?:#|nro\.?|num\.?|numero)?\s*\d+[a-zA-Z]?(?:\s*-\s*\d+)?\b"

# Patrones para conjunciones/preposiciones comunes en ubicaciones
CONJUNCIONES_REGEX = r"(?i)\b(?:en|cerca de|entre|esquina con|al lado de|frente a|junto a|sobre|por|hacia|hasta|desde|a la altura de)\b"

# Patrón para códigos postales colombianos
POSTAL_CODE_REGEX = r"(?i)\b\d{6}\b(?=.*(?:Colombia|Colombiano|Colombiana))"

# Lista predefinida de principales ciudades colombianas para respaldo
PRINCIPALES_CIUDADES_COLOMBIA = [
    "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", 
    "Cúcuta", "Soledad", "Ibagué", "Bucaramanga", "Soacha", 
    "Santa Marta", "Villavicencio", "Bello", "Pereira", "Valledupar", 
    "Manizales", "Montería", "Pasto", "Buenaventura", "Neiva"
]

# Lista predefinida de departamentos de Colombia para respaldo
DEPARTAMENTOS_COLOMBIA = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bolívar", "Boyacá", 
    "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó", "Córdoba", 
    "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira", "Magdalena", 
    "Meta", "Nariño", "Norte de Santander", "Putumayo", "Quindío", "Risaralda", 
    "San Andrés y Providencia", "Santander", "Sucre", "Tolima", "Valle del Cauca", 
    "Vaupés", "Vichada"
]

class ColombianLocationRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado de ubicaciones para Colombia utilizando py-countries-states-cities-database.
    Detecta direcciones, ciudades, departamentos, municipios y otros lugares relevantes.
    """
    
    def __init__(self, supported_language="es"):
        """
        Inicializa el reconocedor de ubicaciones colombianas.
        
        Args:
            supported_language (str): Lenguaje soportado (default: "es").
        """
        # Obtener las ubicaciones colombianas
        self.colombian_cities = self._get_colombian_locations()
        
        # Crear el patrón de ciudades, si tenemos ciudades disponibles
        if self.colombian_cities:
            cities_regex = r"(?i)\b(?:{cities})\b".format(cities="|".join(self.colombian_cities))
            logger.info(f"Patrón de ciudades creado con {len(self.colombian_cities)} ubicaciones")
        else:
            # Patrón genérico para ciudades si no tenemos la lista
            cities_regex = r"(?i)\b(?:bogot[aá]|medell[ií]n|cali|barranquilla|cartagena|c[uú]cuta|soledad|ibagu[eé]|bucaramanga|soacha|santa\s+marta|villavicencio|bello|pereira|valledupar|manizales|monter[ií]a|pasto|buenaventura|neiva|palmira|armenia|popay[aá]n|sincelejo|itagui|itag[üu][ií]|floridablanca|envigado|tulu[aá]|dosquebradas|tunja|gir[oó]n|apartad[oó]|florencia|uribia|ipiales|turbo|maicao|piedecuesta)\b"
            logger.info("Usando patrón genérico de ciudades")
        
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
        Obtiene dinámicamente todas las entidades territoriales colombianas.
        
        Returns:
            list: Lista de nombres de entidades territoriales.
        """
        if not csc_db.available:
            logger.warning("No se pueden obtener ubicaciones colombianas: biblioteca no disponible")
            return self._get_fallback_locations()
            
        try:
            # Obtener ciudades y estados de Colombia (código CO)
            cities = []
            cities_data = csc_db.get_cities_for_country('CO')
            cities = [city['name'] for city in cities_data if 'name' in city]
            
            states = []
            states_data = csc_db.get_states_for_country('CO')
            states = [state['name'] for state in states_data if 'name' in state]
            
            # Si no obtuvimos datos, intentar con get_country_data
            if not cities and not states:
                country_data = csc_db.get_country_data('CO')
                if country_data and 'states' in country_data:
                    states = [state['name'] for state in country_data['states'] if 'name' in state]
                    # Intentar extraer ciudades de los estados
                    for state in country_data.get('states', []):
                        if 'cities' in state:
                            cities.extend([city['name'] for city in state['cities'] if 'name' in city])
                
            all_locations = list(set(cities + states))
            
            if not all_locations:
                logger.warning("No se encontraron datos de ubicaciones colombianas en la base de datos.")
                return self._get_fallback_locations()
                
            return all_locations
        except Exception as e:
            logger.error(f"Error al obtener ubicaciones colombianas: {e}")
            return self._get_fallback_locations()
            
    def _get_fallback_locations(self):
        """Obtiene una lista de ubicaciones predefinidas como respaldo."""
        logger.info("Usando lista predefinida de ubicaciones colombianas como respaldo")
        return PRINCIPALES_CIUDADES_COLOMBIA + DEPARTAMENTOS_COLOMBIA
    def validate_result(self, pattern_text):
        """
        Método para validar si el texto encontrado es realmente una ubicación colombiana.
        
        Args:
            pattern_text (str): El texto que coincide con el patrón.
            
        Returns:
            bool: True si el texto es una ubicación válida, False en caso contrario.
        """
        pattern_text = pattern_text.lower()
        
        # Palabras que pueden indicar falsos positivos
        false_positive_words = ['usuario', 'nombre', 'apellido', 'persona', 'empresa', 'cliente']
        
        # Verifica si es una dirección
        address_keywords = ['calle', 'carrera', 'avenida', 'diagonal', 'transversal', 'manzana', 'barrio', 
                            'cra', 'av', 'tv', 'dg', 'mz']
        is_address = any(word in pattern_text for word in address_keywords)
        
        # Verifica si coincide con una ciudad o departamento
        is_location = False
        
        if csc_db.available:
            try:
                # Obtener ciudades y estados de Colombia
                states_data = csc_db.get_states_for_country('CO')
                cities_data = csc_db.get_cities_for_country('CO')
                
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
                # Fallback a la validación básica
                is_location = self._validate_with_fallback_lists(pattern_words)
        else:
            # Si no tenemos la biblioteca disponible, usamos listas de respaldo
            pattern_words = pattern_text.split()
            is_location = self._validate_with_fallback_lists(pattern_words)
        
        # Verificar si es un falso positivo
        is_false_positive = any(word in pattern_text for word in false_positive_words)
        
        # Devolver True si parece una ubicación y no un falso positivo
        return (is_address or is_location) and not is_false_positive
        
    def _validate_with_fallback_lists(self, words):
        """
        Valida palabras contra listas de respaldo de ciudades y departamentos.
        
        Args:
            words (list): Lista de palabras a validar.
            
        Returns:
            bool: True si alguna palabra coincide con una ubicación conocida.
        """
        # Convertir listas de respaldo a minúsculas para comparación
        common_cities = [city.lower() for city in PRINCIPALES_CIUDADES_COLOMBIA]
        common_departments = [dept.lower() for dept in DEPARTAMENTOS_COLOMBIA]
        
        # Buscar coincidencias
        for word in words:
            if len(word) > 3:  # Ignorar palabras muy cortas
                if any(city_name in word or word in city_name for city_name in common_cities):
                    return True
                if any(dept_name in word or word in dept_name for dept_name in common_departments):
                    return True
        
        return False

    def analyze(self, text, entities, nlp_artifacts=None):
        """
        Sobrescribe el método analyze para realizar validaciones adicionales
        
        Args:
            text (str): El texto a analizar.
            entities (list): Lista de entidades a buscar.
            nlp_artifacts (NlpArtifacts, optional): Artefactos NLP adicionales.
            
        Returns:
            List[RecognizerResult]: Lista de resultados validados del reconocedor.
        """
        # Llamar al método analyze de la clase padre
        results = super().analyze(text, entities, nlp_artifacts)
        
        # Filtrar resultados usando validate_result
        validated_results = [result for result in results if self.validate_result(text[result.start:result.end])]
        
        return validated_results

def query_location_data(query_type, query_value):
    """
    Consulta datos específicos de la división político-administrativa de Colombia.
    
    Args:
        query_type (str): 'municipality' (ciudad), 'department' (estado/departamento), 'code' (código identificador).
        query_value (str): Valor a consultar (nombre o código).
        
    Returns:
        dict o list: Información encontrada o None si no se encuentra.
    """
    if not csc_db.available:
        logger.error("py-countries-states-cities-database no está disponible para realizar consultas.")
        return None
    
    try:
        if query_type == 'municipality':
            # Buscar ciudad por nombre (aproximado)
            query_value_lower = query_value.lower()
            cities_data = csc_db.get_cities_for_country('CO')
            found_cities = []
            
            for city in cities_data:
                if 'name' in city and query_value_lower in city['name'].lower():
                    # Buscar el estado al que pertenece la ciudad
                    state_code = city.get('state_code', '')
                    states_data = csc_db.get_states_for_country('CO')
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
            states_data = csc_db.get_states_for_country('CO')
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
                code_id = str(query_value)  # Convertir a string para comparación
                # Buscar en estados
                states_data = csc_db.get_states_for_country('CO')
                for state in states_data:
                    if str(state.get('id', '')) == code_id:
                        return {'code': state.get('id', ''), 'department': state.get('name', '')}
                
                # Buscar en ciudades
                cities_data = csc_db.get_cities_for_country('CO')
                for city in cities_data:
                    if str(city.get('id', '')) == code_id:
                        # Buscar el estado al que pertenece la ciudad
                        state_code = city.get('state_code', '')
                        states_data = csc_db.get_states_for_country('CO')
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