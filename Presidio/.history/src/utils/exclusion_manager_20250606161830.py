"""
Módulo para gestionar y mantener las listas de exclusión para la anonimización.
Permite añadir/eliminar términos seguros en tiempo de ejecución.
"""

from typing import List, Dict, Set, Optional
import re
from src.utils.filter_lists import (
    TECH_TERMS, PERSON_SAFE_TERMS, LOCATION_SAFE_TERMS, NRP_SAFE_TERMS,
    PAN_SAFE_TERMS, DATETIME_SAFE_TERMS, URL_SAFE_TERMS,
    CONFIDENCE_THRESHOLDS, REGEX_FILTERS, ORGANIZATIONS
)

class ExclusionManager:
    """
    Clase para gestionar las listas de exclusión de términos para la anonimización.
    Permite añadir o eliminar términos de las listas de forma dinámica.
    """
    
    def __init__(self):
        # Inicializar listas de exclusión desde el módulo filter_lists
        self.tech_terms = set(TECH_TERMS)
        self.organizations = set(ORGANIZATIONS)
        self.safe_terms_by_type = {
            "PERSON": set(PERSON_SAFE_TERMS),
            "LOCATION": set(LOCATION_SAFE_TERMS),
            "NRP": set(NRP_SAFE_TERMS),
            "IN_PAN": set(PAN_SAFE_TERMS),
            "DATE_TIME": set(DATETIME_SAFE_TERMS),
            "URL": set(URL_SAFE_TERMS),
        }
        self.confidence_thresholds = dict(CONFIDENCE_THRESHOLDS)
        self.regex_filters = dict(REGEX_FILTERS)
        
        # Compilar el patrón regex para términos técnicos
        self._update_tech_pattern()
    
    def _update_tech_pattern(self):
        """Actualiza el patrón regex para términos técnicos y organizaciones"""
        all_terms = list(self.tech_terms) + list(self.organizations)
        if all_terms:
            self.tech_pattern = re.compile(
                r'\b(' + '|'.join(re.escape(term) for term in all_terms) + r')\b', 
                re.IGNORECASE
            )
        else:
            self.tech_pattern = None
    
    def add_tech_term(self, term: str) -> None:
        """
        Añade un término técnico a la lista de exclusión general
        
        Args:
            term: Término técnico a añadir
        """
        self.tech_terms.add(term)
        self._update_tech_pattern()
    
    def add_safe_term_for_entity(self, term: str, entity_type: str) -> None:
        """
        Añade un término a la lista de exclusión específica para un tipo de entidad
        
        Args:
            term: Término a añadir
            entity_type: Tipo de entidad (PERSON, LOCATION, etc.)
        """
        if entity_type in self.safe_terms_by_type:
            self.safe_terms_by_type[entity_type].add(term)
        else:
            self.safe_terms_by_type[entity_type] = {term}
    
    def add_organization(self, org_name: str) -> None:
        """
        Añade una organización a la lista de exclusión
        
        Args:
            org_name: Nombre de la organización
        """
        self.organizations.add(org_name)
        self._update_tech_pattern()
    
    def remove_term(self, term: str, entity_type: Optional[str] = None) -> bool:
        """
        Elimina un término de la lista correspondiente
        
        Args:
            term: Término a eliminar
            entity_type: Tipo de entidad (si es None, se busca en términos técnicos y organizaciones)
            
        Returns:
            bool: True si el término fue eliminado, False si no existía
        """
        if entity_type is None:
            # Intentar eliminar de términos técnicos y organizaciones
            tech_removed = term in self.tech_terms and self.tech_terms.remove(term)
            org_removed = term in self.organizations and self.organizations.remove(term)
            
            if tech_removed or org_removed:
                self._update_tech_pattern()
                return True
            return False
        
        elif entity_type in self.safe_terms_by_type:
            # Eliminar de la lista específica de entidad
            if term in self.safe_terms_by_type[entity_type]:
                self.safe_terms_by_type[entity_type].remove(term)
                return True
        
        return False
    
    def update_threshold(self, entity_type: str, threshold: float) -> None:
        """
        Actualiza el umbral de confianza para un tipo de entidad
        
        Args:
            entity_type: Tipo de entidad
            threshold: Nuevo umbral (0.0 a 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.confidence_thresholds[entity_type] = threshold
    
    def set_regex_filter(self, entity_type: str, pattern: str) -> None:
        """
        Establece o actualiza un patrón regex para filtrar un tipo de entidad
        
        Args:
            entity_type: Tipo de entidad
            pattern: Patrón regex como cadena
        """
        try:
            # Verificar que el patrón sea válido
            re.compile(pattern)
            self.regex_filters[entity_type] = pattern
        except re.error:
            raise ValueError(f"El patrón regex '{pattern}' es inválido")
    
    def get_all_terms_for_entity(self, entity_type: str) -> List[str]:
        """
        Obtiene todos los términos seguros para un tipo de entidad específico
        
        Args:
            entity_type: Tipo de entidad
            
        Returns:
            Lista de términos seguros para ese tipo de entidad
        """
        if entity_type in self.safe_terms_by_type:
            return list(self.safe_terms_by_type[entity_type])
        return []
    
    def get_tech_terms(self) -> List[str]:
        """
        Obtiene todos los términos técnicos generales
        
        Returns:
            Lista de términos técnicos
        """
        return list(self.tech_terms)
    
    def get_organizations(self) -> List[str]:
        """
        Obtiene todas las organizaciones registradas
        
        Returns:
            Lista de nombres de organizaciones
        """
        return list(self.organizations)
    
    def export_to_file(self, filename: str) -> bool:
        """
        Exporta las configuraciones actuales a un archivo Python
        
        Args:
            filename: Ruta del archivo para guardar la configuración
            
        Returns:
            True si la exportación fue exitosa
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('"""\nConfiguraciones de exclusión para anonimización\nArchivo generado automáticamente\n"""\n\n')
                
                # Exportar términos técnicos
                f.write('# Términos técnicos generales\n')
                f.write('TECH_TERMS = [\n')
                for term in sorted(self.tech_terms):
                    f.write(f'    "{term}",\n')
                f.write(']\n\n')
                
                # Exportar términos por tipo de entidad
                for entity_type, terms in self.safe_terms_by_type.items():
                    f.write(f'# Términos seguros para {entity_type}\n')
                    f.write(f'{entity_type}_SAFE_TERMS = [\n')
                    for term in sorted(terms):
                        f.write(f'    "{term}",\n')
                    f.write(']\n\n')
                
                # Exportar organizaciones
                f.write('# Organizaciones\n')
                f.write('ORGANIZATIONS = [\n')
                for org in sorted(self.organizations):
                    f.write(f'    "{org}",\n')
                f.write(']\n\n')
                
                # Exportar umbrales de confianza
                f.write('# Umbrales de confianza\n')
                f.write('CONFIDENCE_THRESHOLDS = {\n')
                for entity_type, threshold in self.confidence_thresholds.items():
                    f.write(f'    "{entity_type}": {threshold},\n')
                f.write('}\n\n')
                
                # Exportar filtros regex
                f.write('# Filtros regex\n')
                f.write('REGEX_FILTERS = {\n')
                for entity_type, pattern in self.regex_filters.items():
                    f.write(f'    "{entity_type}": r\'{pattern}\',\n')
                f.write('}\n')
                
            return True
        except Exception as e:
            print(f"Error al exportar configuración: {str(e)}")
            return False
