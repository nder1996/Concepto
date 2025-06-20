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
        "excluded_words": ["persona", "usuario", "cliente", "empresa", "documento"],
        
        # Filtros para falsos positivos
        "false_positive_patterns": [
            r"identificac",
            r"documento",
            r"email",
            r"teléfono"
        ]
    }    # Configuración SIMPLIFICADA por tipo de ubicación (solo lo esencial)
    _LOCATIONS = {
        "ADDRESS": {
            "name": "Dirección Colombiana",
            "keywords": ["dirección", "calle", "carrera", "avenida", "transversal", "diagonal", "cra", "av", "cl"],
            "pattern": r"(?i)(?:calle|carrera|avenida|transversal|diagonal|cra?|av|cl)[\s\w#-]+(?:,[\s\w]+)*",
            "score": 0.95
        },
        "CITY": {
            "name": "Ciudad",
            "keywords": ["ciudad", "municipio", "localidad"],
            "pattern": None,  # Se construye dinámicamente
            "score": 0.85
        },
        "DEPARTMENT": {
            "name": "Departamento",
            "keywords": ["departamento", "estado"],
            "pattern": None,  # Se construye dinámicamente
            "score": 0.90
        }
    }

    def __init__(self, supported_language="es"):
        # Cargar datos dinámicamente
        self.colombia_data = self._load_colombia_data()
        
        # Construir patrones dinámicos
        self._update_location_patterns()
        
        patterns = self._build_simple_patterns()
        context = self._build_simple_context()
        
        super().__init__(
            supported_entity=self.ENTITY,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name="ColombianLocationRecognizer"
        )

    def _load_colombia_data(self):
        """Carga datos desde geonamescache siguiendo el mismo patrón"""
        data = {'cities': [], 'departments': []}
        
        try:
            import geonamescache
            
            logger.info("📊 Cargando datos de Colombia desde GeonamesCache...")
            gc = geonamescache.GeonamesCache()
            cities = gc.get_cities()
            
            # Filtrar ciudades de Colombia
            colombia_cities = []
            for city in cities.values():
                if city.get('countrycode') == 'CO':
                    name = city.get('name', '').strip().lower()
                    if name and len(name) >= 3 and self._is_valid_city_name(name):
                        colombia_cities.append(name)
            
            # Ordenar por relevancia (más largos primero)
            colombia_cities.sort(key=len, reverse=True)
            
            data['cities'] = colombia_cities[:200]  # Tomar solo los 200 más importantes
            data['departments'] = self._get_colombia_departments_from_geonames(gc)
            
            logger.info(f"✅ Cargadas {len(data['cities'])} ciudades, {len(data['departments'])} departamentos")
            return data
            
        except ImportError:
            logger.warning("geonamescache no disponible, usando datos básicos")
            return self._get_fallback_data()
        except Exception as e:
            logger.error(f"Error cargando geonamescache: {e}")
            return self._get_fallback_data()

    def _is_valid_city_name(self, name):
        """Validación simple de nombres de ciudades"""
        # Filtrar nombres problemáticos
        problematic = ['san', 'santa', 'el', 'la', 'las', 'los', 'de', 'del']
        return name not in problematic and len(name) >= 3

    def _get_colombia_departments_from_geonames(self, gc):
        """Obtiene departamentos SOLO desde geonamescache"""
        try:
            # geonamescache también tiene datos de subdivisiones administrativas
            countries = gc.get_countries()
            colombia = countries.get('CO')
            
            if colombia:
                # Intentar obtener subdivisiones (departamentos/estados)
                # Nota: algunos datos pueden estar en get_us_states pero para otros países
                # necesitamos usar la API de ciudades y extraer los estados
                departments = set()
                
                # Extraer departamentos únicos desde las ciudades
                cities = gc.get_cities()
                for city in cities.values():
                    if city.get('countrycode') == 'CO':
                        admin1 = city.get('admin1code', '')
                        admin1_name = city.get('admin1', '')
                        if admin1_name and len(admin1_name) >= 3:
                            departments.add(admin1_name.lower().strip())
                
                departments_list = list(departments)
                logger.info(f"📍 Departamentos extraídos desde ciudades: {len(departments_list)}")
                return departments_list
            
            return []
            
        except Exception as e:
            logger.error(f"Error extrayendo departamentos: {e}")
            return []

    def _get_fallback_data(self):
        """Solo fallback MÍNIMO si geonamescache falla completamente"""
        logger.warning("⚠️ geonamescache falló completamente - usando fallback mínimo")
        return {
            'cities': [],  # SIN datos quemados
            'departments': []  # SIN datos quemados
        }

    def _update_location_patterns(self):
        """Actualiza patrones con datos dinámicos"""
        # Patrón para ciudades
        if self.colombia_data.get('cities'):
            cities_escaped = [re.escape(city) for city in self.colombia_data['cities']]
            self._LOCATIONS["CITY"]["pattern"] = r"(?:" + "|".join(cities_escaped) + r")"
        
        # Patrón para departamentos
        if self.colombia_data.get('departments'):
            deps_escaped = [re.escape(dep) for dep in self.colombia_data['departments']]
            self._LOCATIONS["DEPARTMENT"]["pattern"] = r"(?:" + "|".join(deps_escaped) + r")"

    def _build_simple_patterns(self) -> List[Pattern]:
        """Construye patrones siguiendo el mismo patrón que ID recognizer"""
        patterns = []
        
        for loc_type, config in self._LOCATIONS.items():
            if not config.get("pattern"):
                continue
                
            # Patrón 1: Con contexto (alta confianza)
            if config.get("keywords"):
                keywords_regex = "|".join(config["keywords"])
                pattern_with_context = f"\\b(?:{keywords_regex})\\s*[:=]?\\s*({config['pattern']})\\b"
                
                patterns.append(Pattern(
                    name=f"{loc_type.lower()}_with_context",
                    regex=pattern_with_context,
                    score=config["score"]
                ))
            
            # Patrón 2: Solo ubicación (confianza moderada)
            patterns.append(Pattern(
                name=f"{loc_type.lower()}_direct",
                regex=f"\\b({config['pattern']})\\b",
                score=config["score"] - 0.1  # Ligeramente menor confianza
            ))
        
        return patterns

    def _build_simple_context(self) -> List[str]:
        """Lista simple de palabras clave"""
        context = []
        for config in self._LOCATIONS.values():
            if config.get("keywords"):
                context.extend(config["keywords"])
        return list(set(context))

    def _is_false_positive(self, text: str) -> bool:
        """Detecta falsos positivos siguiendo el mismo patrón"""
        text_lower = text.lower()
        
        # Filtrar palabras problemáticas
        if text_lower in self._SIMPLE_CONFIG["excluded_words"]:
            return True
        
        # Filtrar patrones problemáticos
        for pattern in self._SIMPLE_CONFIG["false_positive_patterns"]:
            if re.search(pattern, text_lower):
                return True
                
        return False

    def _get_context(self, text: str, start: int, end: int) -> str:
        """Extrae contexto con ventana reducida"""
        window = self._SIMPLE_CONFIG["context_window"]
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].lower()

    def _validate_location(self, loc_text: str, context: str) -> Tuple[bool, str, float]:
        """Validación simplificada siguiendo el mismo patrón"""
        loc_text = loc_text.strip()
        
        # Filtrar falsos positivos
        if self._is_false_positive(loc_text):
            return False, "", 0.0

        candidates = []
        
        # Nivel 1: Buscar por tipo de ubicación
        for loc_type, config in self._LOCATIONS.items():
            if not config.get("pattern"):
                continue
                
            # Verificar si coincide con el patrón
            if re.fullmatch(config["pattern"], loc_text, re.IGNORECASE):
                
                # Contar palabras clave en contexto
                keyword_count = 0
                if config.get("keywords"):
                    keyword_count = sum(1 for keyword in config["keywords"] 
                                     if keyword in context)
                
                if keyword_count > 0:
                    # Mayor confianza con más palabras clave
                    confidence = min(0.95, config["score"] + (keyword_count * 0.05))
                    candidates.append((loc_type, confidence))
                else:
                    # Confianza base
                    candidates.append((loc_type, config["score"]))

        # Nivel 2: Validación adicional para direcciones
        if self._looks_like_address(loc_text):
            candidates.append(("ADDRESS", 0.90))

        # Retornar el mejor candidato
        if candidates:
            loc_type, confidence = max(candidates, key=lambda x: x[1])
            return True, loc_type, confidence
            
        return False, "", 0.0

    def _looks_like_address(self, text):
        """Detecta estructura de dirección colombiana"""
        text_lower = text.lower()
        address_indicators = [
            r'\bcalle\s+\d+',
            r'\bcarrera\s+\d+',
            r'\bcra\s+\d+',
            r'\bavenida\b',
            r'#\s*\d+[-–]\d+',
            r'\bapto\b',
            r'\binterior\b'
        ]
        
        return any(re.search(pattern, text_lower) for pattern in address_indicators)

    def analyze(self, text: str, nlp_artifacts=None, entities: List[str] = None) -> List[RecognizerResult]:
        """Delegar al análisis base de Presidio"""
        return super().analyze(text=text, nlp_artifacts=nlp_artifacts, entities=entities)


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