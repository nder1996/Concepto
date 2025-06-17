"""
Servicios de análisis especializados utilizando Presidio.

Este módulo proporciona servicios de análisis y procesamiento de datos personales
más allá de las capacidades básicas del motor de Presidio, incluyendo:

- Análisis contextual avanzado para reducir falsos positivos
- Validación de entidades usando modelos adicionales (Flair, etc.)
- Extracción estructurada de información personal
- Análisis estadístico de datos personales en textos grandes
- Verificación de cumplimiento de políticas de privacidad
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import re
import logging
import json
from collections import Counter, defaultdict

# Importar el motor principal de Presidio
from .engine import PresidioEngine

# Intentar importar el validador Flair (opcional)
try:
    from .recognizers.validators.flair_validator import FlairValidator
    FLAIR_DISPONIBLE = True
except ImportError:
    FLAIR_DISPONIBLE = False

# Configurar logger
logger = logging.getLogger("presidio.analysis")

class PresidioAnalysisService:
    """
    Servicios avanzados de análisis de información personal usando Presidio.
    
    Esta clase implementa funcionalidades especializadas para el análisis,
    validación y procesamiento de información personal en textos.
    """
    
    def __init__(self, engine: Optional[PresidioEngine] = None, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el servicio de análisis con un motor de Presidio.
        
        Args:
            engine: Instancia de PresidioEngine. Si es None, se crea una nueva.
            config: Configuración opcional para el servicio de análisis.
        """
        self.logger = logger
        self.logger.info("Inicializando servicio de análisis de Presidio...")
        
        # Configuraciones predeterminadas
        self.config = {
            "umbral_confianza_validacion": 0.75,  # Umbral para validaciones adicionales
            "contexto_ventana": 100,  # Tamaño de la ventana de contexto en caracteres
            "max_entidades_por_categoria": 50,  # Máximo de entidades por categoría en análisis masivo
            "modo_validacion": "medio",  # básico, medio, estricto
            "agrupar_entidades_similares": True,  # Agrupar entidades similares en análisis
            "analisis_estructurado": False  # Extraer relaciones entre entidades
        }
        
        # Actualizar con configuraciones personalizadas si se proporcionan
        if config:
            self.config.update(config)
        
        # Inicializar o usar el motor proporcionado
        self.engine = engine if engine else PresidioEngine()
        
        # Inicializar validador Flair si está disponible
        self.flair_validator = None
        if FLAIR_DISPONIBLE:
            try:
                self.flair_validator = FlairValidator()
                self.logger.info("Validador Flair inicializado correctamente")
            except Exception as e:
                self.logger.warning(f"Error al validar nombre con Flair: {str(e)}")
                validation_info["flair_error"] = str(e)
        
        # Determinar validez final
        is_valid = confidence >= self.config["umbral_confianza_validacion"]
        
        return is_valid, confidence, validation_info
    
    def _validate_phone(self, phone: str, context: str, language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Valida un número telefónico."""
        validation_info = {
            "method": "phone_validation",
            "rules_applied": []
        }
        
        # Limpiar el número de teléfono
        clean_phone = re.sub(r'[\s\-\(\)\+\.]', '', phone)
        
        # Verificar si contiene solo dígitos
        if not clean_phone.isdigit():
            validation_info["rules_applied"].append("non_digit_characters")
            return False, 0.2, validation_info
        
        # Verificar longitud del número
        if len(clean_phone) < 7:
            validation_info["rules_applied"].append("too_short")
            return False, 0.3, validation_info
        elif len(clean_phone) > 15:
            validation_info["rules_applied"].append("too_long")
            return False, 0.3, validation_info
        
        # Verificar patrones de teléfonos colombianos
        is_colombian = False
        confidence = 0.6  # Confianza base
        
        # Formato celular colombiano (10 dígitos iniciando con 3)
        if len(clean_phone) == 10 and clean_phone.startswith('3'):
            validation_info["rules_applied"].append("colombian_mobile")
            is_colombian = True
            confidence = 0.85
        
        # Formato fijo colombiano (7 dígitos para ciudades principales)
        elif len(clean_phone) == 7:
            validation_info["rules_applied"].append("colombian_landline")
            is_colombian = True
            confidence = 0.75
        
        # Número con prefijo internacional (+57)
        elif re.match(r'^(00)?57\d{10}"No se pudo inicializar el validador Flair: {str(e)}")
        
        self.logger.info("Servicio de análisis inicializado correctamente")
    
    def analyze_text(self, 
                    text: str, 
                    language: Optional[str] = None,
                    entities: Optional[List[str]] = None,
                    validate_results: bool = True) -> List[Dict[str, Any]]:
        """
        Analiza un texto con validación adicional de resultados.
        
        Args:
            text: Texto a analizar
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            entities: Lista de tipos de entidades a buscar. Si es None, se buscan todas.
            validate_results: Si es True, aplica validación adicional a los resultados
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades detectadas con detalles adicionales
        """
        # Usar el motor para obtener resultados iniciales
        results = self.engine.analyze(
            text=text, 
            language=language, 
            entities=entities,
            return_decision_process=True
        )
        
        # Si no hay resultados o no se solicita validación, devolver directamente
        if not results or not validate_results:
            return results
        
        # Aplicar validación adicional a los resultados
        validated_results = []
        for result in results:
            # Extraer información básica
            entity_type = result["entity_type"]
            start, end = result["start"], result["end"]
            entity_text = result["text"]
            
            # Obtener contexto para validación
            context_start = max(0, start - self.config["contexto_ventana"])
            context_end = min(len(text), end + self.config["contexto_ventana"])
            context = text[context_start:context_end]
            
            # Validar según el tipo de entidad
            is_valid, confidence, validation_info = self._validate_entity(
                entity_type=entity_type,
                entity_text=entity_text,
                context=context,
                language=language or self.engine.config["idioma_predeterminado"]
            )
            
            # Si la entidad es válida o el modo de validación es básico, incluirla
            if is_valid or self.config["modo_validacion"] == "básico":
                # Añadir información de validación al resultado
                result["validation"] = {
                    "is_valid": is_valid,
                    "confidence": confidence,
                    "method": validation_info.get("method", "rule_based"),
                    "details": validation_info
                }
                
                # Ajustar score combinando con la confianza de validación
                if is_valid:
                    # Dar más peso a la validación adicional
                    result["adjusted_score"] = 0.4 * result["score"] + 0.6 * confidence
                else:
                    # Penalizar score si no pasó la validación pero se incluye por modo básico
                    result["adjusted_score"] = result["score"] * 0.7
                
                validated_results.append(result)
        
        return validated_results
    
    def _validate_entity(self, 
                        entity_type: str, 
                        entity_text: str, 
                        context: str,
                        language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Valida una entidad específica con métodos adicionales.
        
        Args:
            entity_type: Tipo de entidad (ej: "PERSON", "PHONE_NUMBER")
            entity_text: Texto de la entidad
            context: Contexto que rodea a la entidad
            language: Código de idioma (ej: "es", "en")
            
        Returns:
            Tuple[bool, float, Dict]: (es_válido, confianza, información_adicional)
        """
        # Inicializar valores por defecto
        is_valid = True
        confidence = 0.8  # Confianza por defecto
        validation_info = {
            "method": "rule_based",
            "rules_applied": []
        }
        
        # Validación según tipo de entidad
        if entity_type == "PERSON":
            return self._validate_person(entity_text, context, language)
        
        elif entity_type == "PHONE_NUMBER":
            return self._validate_phone(entity_text, context, language)
        
        elif entity_type == "EMAIL_ADDRESS":
            return self._validate_email(entity_text, context, language)
        
        elif entity_type.startswith("CO_ID_NUMBER"):
            return self._validate_document(entity_type, entity_text, context, language)
        
        # Para otros tipos de entidades, usar validación básica
        validation_info["rules_applied"].append("default_validation")
        return is_valid, confidence, validation_info
    
    def _validate_person(self, name: str, context: str, language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Valida un nombre de persona."""
        validation_info = {
            "method": "name_validation",
            "rules_applied": []
        }
        
        # Verificar si es un nombre común/genérico
        common_names = ["usuario", "user", "admin", "administrador", "persona", "name", "nombre"]
        if name.lower() in common_names:
            validation_info["rules_applied"].append("common_name_rejection")
            return False, 0.1, validation_info
        
        # Verificar si tiene estructura de nombre (al menos 2 palabras, iniciales mayúsculas)
        words = name.strip().split()
        if len(words) < 2:
            validation_info["rules_applied"].append("single_word_name")
            # Nombres de una sola palabra son menos confiables
            confidence = 0.5
        else:
            validation_info["rules_applied"].append("multi_word_name")
            # Nombres de múltiples palabras son más confiables
            confidence = 0.7
            
            # Verificar capitalización (nombres suelen tener iniciales mayúsculas)
            properly_capitalized = all(w[0].isupper() for w in words if len(w) > 1)
            if properly_capitalized:
                validation_info["rules_applied"].append("proper_capitalization")
                confidence += 0.1
        
        # Usar Flair para validación adicional si está disponible
        if self.flair_validator:
            try:
                flair_result = self.flair_validator.validate_name(name, context, language)
                validation_info["flair_validation"] = flair_result
                
                if flair_result["is_valid"]:
                    validation_info["rules_applied"].append("flair_confirmed")
                    # Combinar confianza con resultado de Flair
                    confidence = 0.3 * confidence + 0.7 * flair_result["confidence"]
                else:
                    validation_info["rules_applied"].append("flair_rejected")
                    return False, flair_result["confidence"], validation_info
                    
            except Exception as e:
                self.logger.warning(f, clean_phone):
            validation_info["rules_applied"].append("colombian_international")
            is_colombian = True
            confidence = 0.9
        
        # Verificar contexto para aumentar confianza
        phone_context_terms = [
            "tel", "teléfono", "telefono", "celular", "móvil", "movil", 
            "llamar", "comunica", "contacto", "whatsapp", "línea"
        ]
        
        context_lower = context.lower()
        for term in phone_context_terms:
            if term in context_lower:
                validation_info["rules_applied"].append("phone_context_term")
                confidence += 0.1
                break
        
        # Determinar validez final
        is_valid = confidence >= self.config["umbral_confianza_validacion"]
        
        return is_valid, min(1.0, confidence), validation_info
    
    def _validate_email(self, email: str, context: str, language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Valida una dirección de correo electrónico."""
        validation_info = {
            "method": "email_validation",
            "rules_applied": []
        }
        
        # Verificación básica de formato (patrón estándar de email)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"No se pudo inicializar el validador Flair: {str(e)}")
        
        self.logger.info("Servicio de análisis inicializado correctamente")
    
    def analyze_text(self, 
                    text: str, 
                    language: Optional[str] = None,
                    entities: Optional[List[str]] = None,
                    validate_results: bool = True) -> List[Dict[str, Any]]:
        """
        Analiza un texto con validación adicional de resultados.
        
        Args:
            text: Texto a analizar
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            entities: Lista de tipos de entidades a buscar. Si es None, se buscan todas.
            validate_results: Si es True, aplica validación adicional a los resultados
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades detectadas con detalles adicionales
        """
        # Usar el motor para obtener resultados iniciales
        results = self.engine.analyze(
            text=text, 
            language=language, 
            entities=entities,
            return_decision_process=True
        )
        
        # Si no hay resultados o no se solicita validación, devolver directamente
        if not results or not validate_results:
            return results
        
        # Aplicar validación adicional a los resultados
        validated_results = []
        for result in results:
            # Extraer información básica
            entity_type = result["entity_type"]
            start, end = result["start"], result["end"]
            entity_text = result["text"]
            
            # Obtener contexto para validación
            context_start = max(0, start - self.config["contexto_ventana"])
            context_end = min(len(text), end + self.config["contexto_ventana"])
            context = text[context_start:context_end]
            
            # Validar según el tipo de entidad
            is_valid, confidence, validation_info = self._validate_entity(
                entity_type=entity_type,
                entity_text=entity_text,
                context=context,
                language=language or self.engine.config["idioma_predeterminado"]
            )
            
            # Si la entidad es válida o el modo de validación es básico, incluirla
            if is_valid or self.config["modo_validacion"] == "básico":
                # Añadir información de validación al resultado
                result["validation"] = {
                    "is_valid": is_valid,
                    "confidence": confidence,
                    "method": validation_info.get("method", "rule_based"),
                    "details": validation_info
                }
                
                # Ajustar score combinando con la confianza de validación
                if is_valid:
                    # Dar más peso a la validación adicional
                    result["adjusted_score"] = 0.4 * result["score"] + 0.6 * confidence
                else:
                    # Penalizar score si no pasó la validación pero se incluye por modo básico
                    result["adjusted_score"] = result["score"] * 0.7
                
                validated_results.append(result)
        
        return validated_results
    
    def _validate_entity(self, 
                        entity_type: str, 
                        entity_text: str, 
                        context: str,
                        language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Valida una entidad específica con métodos adicionales.
        
        Args:
            entity_type: Tipo de entidad (ej: "PERSON", "PHONE_NUMBER")
            entity_text: Texto de la entidad
            context: Contexto que rodea a la entidad
            language: Código de idioma (ej: "es", "en")
            
        Returns:
            Tuple[bool, float, Dict]: (es_válido, confianza, información_adicional)
        """
        # Inicializar valores por defecto
        is_valid = True
        confidence = 0.8  # Confianza por defecto
        validation_info = {
            "method": "rule_based",
            "rules_applied": []
        }
        
        # Validación según tipo de entidad
        if entity_type == "PERSON":
            return self._validate_person(entity_text, context, language)
        
        elif entity_type == "PHONE_NUMBER":
            return self._validate_phone(entity_text, context, language)
        
        elif entity_type == "EMAIL_ADDRESS":
            return self._validate_email(entity_text, context, language)
        
        elif entity_type.startswith("CO_ID_NUMBER"):
            return self._validate_document(entity_type, entity_text, context, language)
        
        # Para otros tipos de entidades, usar validación básica
        validation_info["rules_applied"].append("default_validation")
        return is_valid, confidence, validation_info
    
    def _validate_person(self, name: str, context: str, language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Valida un nombre de persona."""
        validation_info = {
            "method": "name_validation",
            "rules_applied": []
        }
        
        # Verificar si es un nombre común/genérico
        common_names = ["usuario", "user", "admin", "administrador", "persona", "name", "nombre"]
        if name.lower() in common_names:
            validation_info["rules_applied"].append("common_name_rejection")
            return False, 0.1, validation_info
        
        # Verificar si tiene estructura de nombre (al menos 2 palabras, iniciales mayúsculas)
        words = name.strip().split()
        if len(words) < 2:
            validation_info["rules_applied"].append("single_word_name")
            # Nombres de una sola palabra son menos confiables
            confidence = 0.5
        else:
            validation_info["rules_applied"].append("multi_word_name")
            # Nombres de múltiples palabras son más confiables
            confidence = 0.7
            
            # Verificar capitalización (nombres suelen tener iniciales mayúsculas)
            properly_capitalized = all(w[0].isupper() for w in words if len(w) > 1)
            if properly_capitalized:
                validation_info["rules_applied"].append("proper_capitalization")
                confidence += 0.1
        
        # Usar Flair para validación adicional si está disponible
        if self.flair_validator:
            try:
                flair_result = self.flair_validator.validate_name(name, context, language)
                validation_info["flair_validation"] = flair_result
                
                if flair_result["is_valid"]:
                    validation_info["rules_applied"].append("flair_confirmed")
                    # Combinar confianza con resultado de Flair
                    confidence = 0.3 * confidence + 0.7 * flair_result["confidence"]
                else:
                    validation_info["rules_applied"].append("flair_rejected")
                    return False, flair_result["confidence"], validation_info
                    
            except Exception as e:
                self.logger.warning(f
        if not re.match(email_pattern, email):
            validation_info["rules_applied"].append("invalid_format")
            return False, 0.2, validation_info
        
        # Confianza inicial
        confidence = 0.7
        
        # Verificar partes del email
        local_part, domain = email.split('@', 1)
        
        # Verificar longitud de la parte local
        if len(local_part) > 64:
            validation_info["rules_applied"].append("local_part_too_long")
            return False, 0.3, validation_info
        
        # Verificar formato del dominio
        if '.' not in domain:
            validation_info["rules_applied"].append("invalid_domain_format")
            return False, 0.3, validation_info
        
        # Verificar TLD (Top Level Domain)
        tld = domain.split('.')[-1]
        if len(tld) < 2 or len(tld) > 6:
            validation_info["rules_applied"].append("invalid_tld")
            confidence -= 0.2
        
        # Dominios comunes aumentan la confianza
        common_domains = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com"]
        if domain.lower() in common_domains:
            validation_info["rules_applied"].append("common_domain")
            confidence += 0.15
        
        # Verificar contexto para aumentar confianza
        email_context_terms = [
            "correo", "email", "e-mail", "mail", "electrónico", "electronico", 
            "arroba", "@", "enviar", "contacto", "escribir"
        ]
        
        context_lower = context.lower()
        for term in email_context_terms:
            if term in context_lower:
                validation_info["rules_applied"].append("email_context_term")
                confidence += 0.1
                break
        
        # Determinar validez final
        is_valid = confidence >= self.config["umbral_confianza_validacion"]
        
        return is_valid, min(1.0, confidence), validation_info
    
    def _validate_document(self, entity_type: str, document: str, context: str, language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Valida un documento de identidad colombiano."""
        validation_info = {
            "method": "document_validation",
            "rules_applied": [],
            "document_type": entity_type.replace("CO_ID_NUMBER_", "") if "_" in entity_type else "GENERIC"
        }
        
        # Limpiar el documento
        clean_doc = re.sub(r'[\s\-\.]', '', document)
        
        # Verificar si contiene principalmente dígitos
        digit_ratio = sum(c.isdigit() for c in clean_doc) / len(clean_doc) if clean_doc else 0
        if digit_ratio < 0.7:  # Permitir algunos caracteres no dígitos (como en pasaportes)
            validation_info["rules_applied"].append("insufficient_digits")
            confidence = 0.4
        else:
            confidence = 0.7
            validation_info["rules_applied"].append("sufficient_digits")
        
        # Validaciones específicas según tipo de documento
        doc_type = validation_info["document_type"]
        
        if doc_type == "CC" or doc_type == "GENERIC":
            # Cédula de ciudadanía: típicamente 8-10 dígitos
            if not (7 <= len(clean_doc) <= 10):
                validation_info["rules_applied"].append("invalid_cc_length")
                confidence -= 0.2
            else:
                validation_info["rules_applied"].append("valid_cc_length")
                confidence += 0.1
        
        elif doc_type == "TI":
            # Tarjeta de identidad: 10-11 dígitos
            if not (10 <= len(clean_doc) <= 11):
                validation_info["rules_applied"].append("invalid_ti_length")
                confidence -= 0.2
            else:
                validation_info["rules_applied"].append("valid_ti_length")
                confidence += 0.1
        
        elif doc_type == "CE":
            # Cédula de extranjería: 6-8 caracteres
            if not (5 <= len(clean_doc) <= 8):
                validation_info["rules_applied"].append("invalid_ce_length")
                confidence -= 0.2
            else:
                validation_info["rules_applied"].append("valid_ce_length")
                confidence += 0.1
        
        elif doc_type == "PA":
            # Pasaporte: típicamente alfanumérico, 6-7 caracteres
            if not (6 <= len(clean_doc) <= 7):
                validation_info["rules_applied"].append("invalid_pa_length")
                confidence -= 0.2
            else:
                validation_info["rules_applied"].append("valid_pa_length")
                confidence += 0.1
        
        elif doc_type == "NIT":
            # NIT: 9-10 dígitos + dígito verificador
            if not (9 <= len(clean_doc) <= 11):
                validation_info["rules_applied"].append("invalid_nit_length")
                confidence -= 0.2
            else:
                validation_info["rules_applied"].append("valid_nit_length")
                confidence += 0.1
        
        # Verificar contexto para aumentar confianza
        document_context_terms = {
            "CC": ["cédula", "cedula", "ciudadanía", "ciudadania", "c.c.", "cc"],
            "TI": ["tarjeta", "identidad", "t.i.", "ti"],
            "CE": ["extranjería", "extranjeria", "c.e.", "ce"],
            "PA": ["pasaporte", "pa"],
            "NIT": ["nit", "tributaria", "rut", "n.i.t."],
            "RC": ["registro", "civil", "r.c.", "rc"],
            "PEP": ["permiso", "permanencia", "pep"],
            "GENERIC": ["documento", "identidad", "identificación", "identificacion"]
        }
        
        context_lower = context.lower()
        terms_to_check = document_context_terms.get(doc_type, document_context_terms["GENERIC"])
        
        for term in terms_to_check:
            if term in context_lower:
                validation_info["rules_applied"].append("document_context_term")
                confidence += 0.15
                break
        
        # Determinar validez final
        is_valid = confidence >= self.config["umbral_confianza_validacion"]
        
        return is_valid, min(1.0, confidence), validation_info
    
    def analyze_document(self, 
                        text: str, 
                        language: Optional[str] = None, 
                        include_statistics: bool = True) -> Dict[str, Any]:
        """
        Analiza un documento completo, proporcionando estadísticas y visualizaciones.
        
        Args:
            text: Texto del documento a analizar
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            include_statistics: Si es True, incluye estadísticas sobre las entidades encontradas
            
        Returns:
            Dict[str, Any]: Resultado completo del análisis con estadísticas
        """
        # Analizar el texto con validación
        entities = self.analyze_text(
            text=text,
            language=language,
            validate_results=True
        )
        
        # Preparar resultado base
        result = {
            "text_length": len(text),
            "language": language or self.engine.config["idioma_predeterminado"],
            "entities": entities,
            "total_entities": len(entities)
        }
        
        # Si se solicitan estadísticas, generarlas
        if include_statistics:
            result["statistics"] = self._generate_statistics(entities, text)
        
        return result
    
    def _generate_statistics(self, entities: List[Dict[str, Any]], text: str) -> Dict[str, Any]:
        """Genera estadísticas sobre las entidades encontradas."""
        stats = {
            "entity_counts": {},
            "entity_distribution": {},
            "confidence_ranges": {
                "high": 0,    # > 0.8
                "medium": 0,  # 0.6 - 0.8
                "low": 0      # < 0.6
            },
            "validated_entities": 0,
            "top_entities": {},
            "density": 0  # Entidades por cada 1000 caracteres
        }
        
        # Si no hay entidades, devolver estadísticas vacías
        if not entities:
            return stats
        
        # Contar entidades por tipo
        entity_counter = Counter()
        for entity in entities:
            entity_type = entity["entity_type"]
            entity_counter[entity_type] += 1
            
            # Contar por rango de confianza
            score = entity.get("adjusted_score", entity["score"])
            if score > 0.8:
                stats["confidence_ranges"]["high"] += 1
            elif score > 0.6:
                stats["confidence_ranges"]["medium"] += 1
            else:
                stats["confidence_ranges"]["low"] += 1
            
            # Contar entidades validadas
            if entity.get("validation", {}).get("is_valid", False):
                stats["validated_entities"] += 1
        
        # Almacenar conteos y distribución
        stats["entity_counts"] = dict(entity_counter)
        total_entities = sum(entity_counter.values())
        stats["entity_distribution"] = {
            k: round(v / total_entities * 100, 2) for k, v in entity_counter.items()
        }
        
        # Calcular densidad de entidades
        if len(text) > 0:
            stats["density"] = round(total_entities / (len(text) / 1000), 2)
        
        # Obtener las entidades más comunes por tipo
        top_entities = defaultdict(Counter)
        for entity in entities:
            entity_type = entity["entity_type"]
            entity_text = entity["text"]
            
            # Limitar a max_entidades_por_categoria
            if len(top_entities[entity_type]) < self.config["max_entidades_por_categoria"]:
                top_entities[entity_type][entity_text] += 1
        
        # Convertir a diccionario para serialización JSON
        stats["top_entities"] = {
            k: dict(v.most_common(10)) for k, v in top_entities.items()
        }
        
        return stats
    
    def analyze_multiple_documents(self, 
                                 documents: List[Dict[str, str]], 
                                 language: Optional[str] = None) -> Dict[str, Any]:
        """
        Analiza múltiples documentos, proporcionando estadísticas agregadas.
        
        Args:
            documents: Lista de diccionarios con 'id' y 'text' para cada documento
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            
        Returns:
            Dict[str, Any]: Resultados agregados del análisis
        """
        # Inicializar resultados
        results = {
            "total_documents": len(documents),
            "total_entities": 0,
            "document_results": [],
            "aggregated_statistics": {
                "entity_counts": {},
                "confidence_ranges": {
                    "high": 0,
                    "medium": 0,
                    "low": 0
                },
                "validated_entities": 0,
                "average_density": 0,
                "entities_per_document": 0
            }
        }
        
        # Analizar cada documento
        total_length = 0
        for doc in documents:
            doc_id = doc.get("id", f"doc_{len(results['document_results'])}")
            doc_text = doc.get("text", "")
            
            if not doc_text:
                continue
                
            # Analizar documento
            doc_result = self.analyze_document(
                text=doc_text,
                language=language,
                include_statistics=True
            )
            
            # Añadir ID del documento
            doc_result["document_id"] = doc_id
            
            # Actualizar contadores
            results["total_entities"] += doc_result["total_entities"]
            total_length += doc_result["text_length"]
            
            # Agregar estadísticas
            if "statistics" in doc_result:
                stats = doc_result["statistics"]
                
                # Sumar conteos de entidades
                for entity_type, count in stats["entity_counts"].items():
                    if entity_type not in results["aggregated_statistics"]["entity_counts"]:
                        results["aggregated_statistics"]["entity_counts"][entity_type] = 0
                    results["aggregated_statistics"]["entity_counts"][entity_type] += count
                
                # Sumar rangos de confianza
                for range_key in ["high", "medium", "low"]:
                    results["aggregated_statistics"]["confidence_ranges"][range_key] += \
                        stats["confidence_ranges"][range_key]
                
                # Sumar entidades validadas
                results["aggregated_statistics"]["validated_entities"] += stats["validated_entities"]
            
            # Añadir resultado del documento
            results["document_results"].append(doc_result)
        
        # Calcular estadísticas agregadas
        if results["total_documents"] > 0:
            results["aggregated_statistics"]["entities_per_document"] = \
                round(results["total_entities"] / results["total_documents"], 2)
                
        if total_length > 0:
            results["aggregated_statistics"]["average_density"] = \
                round(results["total_entities"] / (total_length / 1000), 2)
        
        return results
    
    def get_detailed_entity_info(self, entity_type: str) -> Dict[str, Any]:
        """
        Obtiene información detallada sobre un tipo específico de entidad.
        
        Args:
            entity_type: Tipo de entidad (ej: "PERSON", "PHONE_NUMBER")
            
        Returns:
            Dict[str, Any]: Información detallada sobre la entidad
        """
        # Inicializar información
        entity_info = {
            "entity_type": entity_type,
            "description": "",
            "detection_methods": [],
            "validation_methods": [],
            "examples": [],
            "context_words": []
        }
        
        # Información específica según tipo de entidad
        if entity_type == "PERSON":
            entity_info["description"] = "Nombres de personas físicas, incluyendo nombres completos o parciales."
            entity_info["detection_methods"] = ["Reconocimiento de entidades nombradas (NER)", "Patrones lingüísticos", "Análisis contextual"]
            entity_info["validation_methods"] = ["Validación con Flair", "Verificación de estructura de nombres", "Análisis de capitalización"]
            entity_info["examples"] = ["Juan Pérez", "María González", "Dr. Carlos Rodríguez"]
            entity_info["context_words"] = ["señor", "señora", "doctor", "licenciado", "ingeniero", "profesor", "Sr.", "Sra.", "Dr."]
            
        elif entity_type == "PHONE_NUMBER":
            entity_info["description"] = "Números telefónicos en diversos formatos, incluyendo fijos y móviles."
            entity_info["detection_methods"] = ["Patrones regex", "Análisis contextual"]
            entity_info["validation_methods"] = ["Validación de formato", "Verificación de longitud", "Análisis de prefijos"]
            entity_info["examples"] = ["+57 300 123 4567", "601 234 5678", "3001234567"]
            entity_info["context_words"] = ["teléfono", "celular", "móvil", "llamar", "contacto", "whatsapp"]
            
        elif entity_type == "EMAIL_ADDRESS":
            entity_info["description"] = "Direcciones de correo electrónico."
            entity_info["detection_methods"] = ["Patrones regex", "Análisis contextual"]
            entity_info["validation_methods"] = ["Validación de formato", "Verificación de dominio", "Análisis de TLD"]
            entity_info["examples"] = ["usuario@ejemplo.com", "nombre.apellido@empresa.co", "contacto@dominio.com"]
            entity_info["context_words"] = ["correo", "email", "e-mail", "arroba", "contacto", "escribir"]
            
        elif entity_type.startswith("CO_ID_NUMBER"):
            doc_type = entity_type.replace("CO_ID_NUMBER_", "") if "_" in entity_type else "GENERIC"
            
            entity_info["description"] = f"Documento de identidad colombiano tipo {doc_type}."
            entity_info["detection_methods"] = ["Patrones regex", "Análisis contextual", "Reconocimiento de palabras clave"]
            entity_info["validation_methods"] = ["Validación de formato", "Verificación de longitud", "Análisis de contexto"]
            
            if doc_type == "CC" or doc_type == "GENERIC":
                entity_info["examples"] = ["Cédula 1.234.567.890", "C.C. 12345678", "Mi cédula es 87654321"]
                entity_info["context_words"] = ["cédula", "ciudadanía", "cc", "c.c.", "identificación"]
            elif doc_type == "TI":
                entity_info["examples"] = ["T.I. 98765432109", "Tarjeta de identidad 1234567890"]
                entity_info["context_words"] = ["tarjeta", "identidad", "ti", "t.i.", "menor"]
            elif doc_type == "CE":
                entity_info["examples"] = ["CE 123456", "Cédula de extranjería 654321"]
                entity_info["context_words"] = ["extranjería", "ce", "c.e.", "extranjero"]
            elif doc_type == "PA":
                entity_info["examples"] = ["Pasaporte AB123456", "PA CD7890"]
                entity_info["context_words"] = ["pasaporte", "pa", "p.a.", "viaje"]
                
        else:
            entity_info["description"] = f"Entidad de tipo {entity_type}."
            entity_info["detection_methods"] = ["Patrones predefinidos", "Análisis contextual"]
            entity_info["validation_methods"] = ["Validación básica"]
        
        return entity_info
"No se pudo inicializar el validador Flair: {str(e)}")
        
        self.logger.info("Servicio de análisis inicializado correctamente")
    
    def analyze_text(self, 
                    text: str, 
                    language: Optional[str] = None,
                    entities: Optional[List[str]] = None,
                    validate_results: bool = True) -> List[Dict[str, Any]]:
        """
        Analiza un texto con validación adicional de resultados.
        
        Args:
            text: Texto a analizar
            language: Código de idioma (ej: "es", "en"). Si es None, se usa el predeterminado.
            entities: Lista de tipos de entidades a buscar. Si es None, se buscan todas.
            validate_results: Si es True, aplica validación adicional a los resultados
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades detectadas con detalles adicionales
        """
        # Usar el motor para obtener resultados iniciales
        results = self.engine.analyze(
            text=text, 
            language=language, 
            entities=entities,
            return_decision_process=True
        )
        
        # Si no hay resultados o no se solicita validación, devolver directamente
        if not results or not validate_results:
            return results
        
        # Aplicar validación adicional a los resultados
        validated_results = []
        for result in results:
            # Extraer información básica
            entity_type = result["entity_type"]
            start, end = result["start"], result["end"]
            entity_text = result["text"]
            
            # Obtener contexto para validación
            context_start = max(0, start - self.config["contexto_ventana"])
            context_end = min(len(text), end + self.config["contexto_ventana"])
            context = text[context_start:context_end]
            
            # Validar según el tipo de entidad
            is_valid, confidence, validation_info = self._validate_entity(
                entity_type=entity_type,
                entity_text=entity_text,
                context=context,
                language=language or self.engine.config["idioma_predeterminado"]
            )
            
            # Si la entidad es válida o el modo de validación es básico, incluirla
            if is_valid or self.config["modo_validacion"] == "básico":
                # Añadir información de validación al resultado
                result["validation"] = {
                    "is_valid": is_valid,
                    "confidence": confidence,
                    "method": validation_info.get("method", "rule_based"),
                    "details": validation_info
                }
                
                # Ajustar score combinando con la confianza de validación
                if is_valid:
                    # Dar más peso a la validación adicional
                    result["adjusted_score"] = 0.4 * result["score"] + 0.6 * confidence
                else:
                    # Penalizar score si no pasó la validación pero se incluye por modo básico
                    result["adjusted_score"] = result["score"] * 0.7
                
                validated_results.append(result)
        
        return validated_results
    
    def _validate_entity(self, 
                        entity_type: str, 
                        entity_text: str, 
                        context: str,
                        language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Valida una entidad específica con métodos adicionales.
        
        Args:
            entity_type: Tipo de entidad (ej: "PERSON", "PHONE_NUMBER")
            entity_text: Texto de la entidad
            context: Contexto que rodea a la entidad
            language: Código de idioma (ej: "es", "en")
            
        Returns:
            Tuple[bool, float, Dict]: (es_válido, confianza, información_adicional)
        """
        # Inicializar valores por defecto
        is_valid = True
        confidence = 0.8  # Confianza por defecto
        validation_info = {
            "method": "rule_based",
            "rules_applied": []
        }
        
        # Validación según tipo de entidad
        if entity_type == "PERSON":
            return self._validate_person(entity_text, context, language)
        
        elif entity_type == "PHONE_NUMBER":
            return self._validate_phone(entity_text, context, language)
        
        elif entity_type == "EMAIL_ADDRESS":
            return self._validate_email(entity_text, context, language)
        
        elif entity_type.startswith("CO_ID_NUMBER"):
            return self._validate_document(entity_type, entity_text, context, language)
        
        # Para otros tipos de entidades, usar validación básica
        validation_info["rules_applied"].append("default_validation")
        return is_valid, confidence, validation_info
    
    def _validate_person(self, name: str, context: str, language: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Valida un nombre de persona."""
        validation_info = {
            "method": "name_validation",
            "rules_applied": []
        }
        
        # Verificar si es un nombre común/genérico
        common_names = ["usuario", "user", "admin", "administrador", "persona", "name", "nombre"]
        if name.lower() in common_names:
            validation_info["rules_applied"].append("common_name_rejection")
            return False, 0.1, validation_info
        
        # Verificar si tiene estructura de nombre (al menos 2 palabras, iniciales mayúsculas)
        words = name.strip().split()
        if len(words) < 2:
            validation_info["rules_applied"].append("single_word_name")
            # Nombres de una sola palabra son menos confiables
            confidence = 0.5
        else:
            validation_info["rules_applied"].append("multi_word_name")
            # Nombres de múltiples palabras son más confiables
            confidence = 0.7
            
            # Verificar capitalización (nombres suelen tener iniciales mayúsculas)
            properly_capitalized = all(w[0].isupper() for w in words if len(w) > 1)
            if properly_capitalized:
                validation_info["rules_applied"].append("proper_capitalization")
                confidence += 0.1
        
        # Usar Flair para validación adicional si está disponible
        if self.flair_validator:
            try:
                flair_result = self.flair_validator.validate_name(name, context, language)
                validation_info["flair_validation"] = flair_result
                
                if flair_result["is_valid"]:
                    validation_info["rules_applied"].append("flair_confirmed")
                    # Combinar confianza con resultado de Flair
                    confidence = 0.3 * confidence + 0.7 * flair_result["confidence"]
                else:
                    validation_info["rules_applied"].append("flair_rejected")
                    return False, flair_result["confidence"], validation_info
                    
            except Exception as e:
                self.logger.warning(f