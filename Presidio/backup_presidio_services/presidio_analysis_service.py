from typing import List, Dict, Any
from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import re
from src.utils.logger import setup_logger
from src.services.presidio.presidio_nlp_service import PresidioNLPService
from src.services.flair.flair_service import FlairService
from src.config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, ENTITY_THRESHOLDS

class PresidioAnalysisService:
    """
    Servicio para análisis y anonimización de textos utilizando Presidio.
    Utiliza el servicio de NLP de Presidio para las operaciones básicas y
    puede incorporar validación de Flair para entidades de tipo persona.
    """
    
    def __init__(self, presidio_nlp_service: PresidioNLPService, flair_service: FlairService = None):
        """
        Inicializa el servicio de análisis con los servicios necesarios
        
        Args:
            presidio_nlp_service: Servicio de NLP de Presidio ya configurado
            flair_service: Servicio de Flair para validación adicional (opcional)
        """
        self.logger = setup_logger("PresidioAnalysisService")
        self.presidio_nlp_service = presidio_nlp_service
        self.flair_service = flair_service
        self.anonymizer = AnonymizerEngine()
        
        # Configuración de idiomas desde el archivo de configuración
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        
        # Umbrales de confianza por tipo de entidad desde la configuración
        self.entity_thresholds = ENTITY_THRESHOLDS
        
        self.logger.info("Servicio de análisis Presidio inicializado")
    
    def get_entity_thresholds(self, language: str) -> Dict[str, float]:
        """
        Obtiene los umbrales de confianza para cada tipo de entidad según el idioma
        
        Args:
            language: Código de idioma ('es', 'en')
            
        Returns:
            Dict con umbrales por tipo de entidad
        """
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            language = self.default_language
            
        return self.entity_thresholds.get(language)
    
    def analyze_text(self, text: str, language: str = None, entities: List[str] = None) -> List[Dict[str, Any]]:
        """
        Analiza un texto para detectar entidades PII
        
        Args:
            text: Texto a analizar
            language: Idioma del texto ('es', 'en')
            entities: Lista de tipos de entidades a buscar (opcional)
            
        Returns:
            Lista de entidades encontradas con detalles
        """
        if not text or len(text.strip()) == 0:
            self.logger.warning("Texto vacío enviado para análisis")
            return []
            
        # Validar y establecer idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language
        
        self.logger.info(f"Analizando texto ({len(text)} caracteres) en idioma: {language}")
        
        try:
            # Verificar si necesitamos validación especial para personas
            if entities and "PERSON" in entities:
                self.logger.info("Solicitada análisis específico para entidades PERSON")
                person_entities = self.validate_person_entities(text, language)
                
                # Si solo se solicitaron entidades PERSON, devolver solo esas
                if len(entities) == 1:
                    return person_entities
                    
                # Si se solicitaron más entidades, obtener el resto y combinarlas
                other_entities = [e for e in entities if e != "PERSON"]
                other_results = self._analyze_with_presidio(text, language, other_entities)
                
                # Combinar resultados y devolverlos
                return person_entities + other_results
            else:
                # Análisis estándar con Presidio
                return self._analyze_with_presidio(text, language, entities)
                
        except Exception as e:
            self.logger.error(f"Error durante el análisis: {str(e)}")
            return []
    
    def _analyze_with_presidio(self, text: str, language: str, entities: List[str] = None) -> List[Dict[str, Any]]:
        """
        Analiza texto usando el motor estándar de Presidio
        
        Args:
            text: Texto a analizar
            language: Idioma del texto
            entities: Tipos de entidades a buscar (opcional)
            
        Returns:
            Lista de entidades encontradas convertidas a diccionario
        """
        # Obtener el analizador para el idioma especificado
        analyzer = self.presidio_nlp_service.get_analyzer(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return []
            
        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)
        
        # Analizar el texto con el analizador de Presidio
        results = analyzer.analyze(
            text=text,
            language=language,
            entities=entities,
            return_decision_process=True
        )
        
        # Filtrar resultados por umbral según el tipo de entidad
        filtered_results = []
        for result in results:
            entity_type = result.entity_type
            threshold = thresholds.get(entity_type, thresholds["DEFAULT"])
            
            if result.score >= threshold:
                # Convertir ResultRecognizer a diccionario para facilitar el procesamiento
                entity_dict = {
                    "start": result.start,
                    "end": result.end,
                    "score": result.score,
                    "entity_type": result.entity_type,
                    "analysis_explanation": result.analysis_explanation
                }
                
                # Extraer el texto de la entidad
                entity_dict["text"] = text[result.start:result.end]
                
                filtered_results.append(entity_dict)
        
        self.logger.info(f"Entidades encontradas: {len(filtered_results)} (después de filtrar por umbral)")
        return filtered_results
        
    def validate_person_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        """
        Valida las entidades de tipo PERSON utilizando múltiples métodos:
        1. Reconocedor predeterminado de Presidio con umbral muy bajo
        2. Detección de patrones de palabras capitalizadas como posibles nombres
        3. Validación con Flair para confirmar si realmente son nombres de persona
        
        Args:
            text: Texto a analizar
            language: Idioma del texto (es, en)
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades validadas con información detallada
        """
        import re
        
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language
            
        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)
        person_threshold = 0.05  # Umbral extremadamente bajo para Presidio
        
        # Lista para almacenar todas las entidades candidatas encontradas por cualquier método
        all_candidates = []
        
        # Seleccionar el analizador específico para el idioma
        analyzer = self.presidio_nlp_service.get_analyzer(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return []
            
        # Registrar análisis inicial
        self.logger.info(f"Detectando nombres de personas en texto: '{text[:50]}...' en idioma: {language}")
        self.logger.info(f"Usando métodos múltiples para detección de nombres (Presidio + patrones + Flair)")
        
        # ------------------------------------------------------------------------
        # MÉTODO 1: UTILIZAR PRESIDIO CON UMBRAL MUY BAJO
        # ------------------------------------------------------------------------
        
        # Analizar el texto específicamente para entidades de tipo PERSON
        presidio_results = analyzer.analyze(text=text, language=language, entities=["PERSON"])
        self.logger.info(f"Total de nombres detectados por Presidio: {len(presidio_results)}")
        
        # Agregar los resultados de Presidio a los candidatos si superan el umbral mínimo
        for r in presidio_results:
            if r.entity_type == "PERSON" and r.score >= person_threshold:
                name_text = text[r.start:r.end].strip()
                self.logger.info(f"Candidato Presidio: '{name_text}', Score: {r.score}")
                
                # Extraer contexto para validación Flair
                inicio_contexto = max(0, r.start - 50)
                fin_contexto = min(len(text), r.end + 50)
                contexto = text[inicio_contexto:fin_contexto]
                
                all_candidates.append({
                    "entity_type": "PERSON",
                    "nombre": name_text,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "language": language,
                    "contexto": contexto,
                    "metodo": "presidio"
                })
        
        # ------------------------------------------------------------------------
        # MÉTODO 2: BUSCAR PATRONES DE POSIBLES NOMBRES
        # ------------------------------------------------------------------------
        
        # Patrones que pueden indicar nombres de personas en español
        # - Secuencia de 2-4 palabras capitalizadas
        # - Palabras como "compañero", "señor", "señora", etc. seguidas de palabras capitalizadas
        
        # Dividir el texto en segmentos para análisis
        segments = re.split(r'[,.:;()\[\]{}"\']', text)
        
        for segment in segments:
            # Buscar secuencias de palabras capitalizadas (posibles nombres completos)
            words = segment.strip().split()
            capitalized_sequences = []
            current_sequence = []
            
            for word in words:
                # Si la palabra empieza con mayúscula y no es principio de oración
                if word and word[0].isupper() and len(word) > 1:
                    # Si es una palabra que típicamente no forma parte de nombres (artículos, etc.)
                    if word.lower() in ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del']:
                        # Solo seguir si ya se inició una secuencia
                        if current_sequence:
                            current_sequence.append(word)
                    else:
                        current_sequence.append(word)
                else:
                    # Si tenemos una secuencia, guardarla si tiene al menos 2 palabras
                    if len(current_sequence) >= 2:
                        capitalized_sequences.append(" ".join(current_sequence))
                    current_sequence = []
            
            # No olvidar la última secuencia
            if len(current_sequence) >= 2:
                capitalized_sequences.append(" ".join(current_sequence))
                
            # Procesar secuencias encontradas
            for sequence in capitalized_sequences:
                # Buscar la posición en el texto original
                start_pos = text.find(sequence)
                
                if start_pos >= 0:
                    end_pos = start_pos + len(sequence)
                    
                    # Calcular un score sintético (menor que el umbral de Presidio para forzar validación)
                    synth_score = 0.40 if len(sequence.split()) >= 3 else 0.30
                    
                    # Extraer contexto para validación Flair
                    inicio_contexto = max(0, start_pos - 50)
                    fin_contexto = min(len(text), end_pos + 50)
                    contexto = text[inicio_contexto:fin_contexto]
                    
                    self.logger.info(f"Candidato por patrón: '{sequence}', Score: {synth_score}")
                    
                    all_candidates.append({
                        "entity_type": "PERSON",
                        "nombre": sequence,
                        "start": start_pos,
                        "end": end_pos,
                        "score": synth_score,  # Score más bajo para forzar validación por Flair
                        "language": language,
                        "contexto": contexto,
                        "metodo": "patron"
                    })
                    
        # ------------------------------------------------------------------------
        # VALIDACIÓN CON FLAIR (SI ESTÁ DISPONIBLE)
        # ------------------------------------------------------------------------
        
        validated_entities = []
        need_validation = []
        
        # Primero procesar las entidades con alta confianza de Presidio que no necesitan validación
        for candidate in all_candidates:
            # Si es un resultado de Presidio con alta confianza, aceptarlo directamente
            if (candidate["metodo"] == "presidio" and 
                candidate["score"] >= thresholds.get("PERSON", thresholds["DEFAULT"])):
                
                self.logger.info(f"Aceptando directamente: '{candidate['nombre']}' (Score: {candidate['score']})")
                
                # Convertir al formato de salida estándar
                validated_entities.append({
                    "start": candidate["start"],
                    "end": candidate["end"],
                    "score": candidate["score"],
                    "entity_type": "PERSON",
                    "text": candidate["nombre"]
                })
            else:
                # Los demás candidatos necesitan validación adicional
                need_validation.append(candidate)
                
        # Si tenemos Flair disponible, validar los candidatos que lo necesitan
        if self.flair_service and need_validation:
            self.logger.info(f"Validando {len(need_validation)} candidatos con Flair...")
            
            for candidate in need_validation:
                # Validar el candidato con Flair
                resultado_flair = self.flair_service.validar_nombre(
                    texto=text,
                    nombre=candidate["nombre"],
                    contexto=candidate["contexto"],
                    start=candidate["start"],
                    end=candidate["end"]
                )
                
                # Si Flair validó el nombre como persona, agregarlo a los resultados
                if resultado_flair["es_valido"]:
                    # Usar el nombre normalizado y la confianza de Flair
                    nombre_normalizado = resultado_flair["nombre_normalizado"]
                    confianza_flair = resultado_flair["confianza"]
                    
                    self.logger.info(f"Flair VALIDÓ el nombre: '{nombre_normalizado}' (Confianza: {confianza_flair:.4f})")
                    
                    # Convertir al formato de salida estándar
                    validated_entities.append({
                        "start": candidate["start"],
                        "end": candidate["end"],
                        "score": confianza_flair,  # Usar la confianza de Flair
                        "entity_type": "PERSON",
                        "text": nombre_normalizado,
                        "validation": {
                            "method": "flair",
                            "original_score": candidate["score"],
                            "flair_score": confianza_flair
                        }
                    })
                else:
                    self.logger.info(f"Flair RECHAZÓ el nombre: '{candidate['nombre']}' (Motivo: {resultado_flair['motivo']})")
        else:
            # Si no tenemos Flair, usar solo los candidatos de alta confianza
            self.logger.info("Flair no está disponible, usando solo resultados de alta confianza de Presidio")
            
        self.logger.info(f"Total de nombres validados: {len(validated_entities)}")
        return validated_entities
    
    def anonymize_text(self, text: str, language: str = None, entities: List[str] = None) -> Dict[str, Any]:
        """
        Anonimiza un texto utilizando los resultados del análisis
        
        Args:
            text: Texto a anonimizar
            language: Idioma del texto
            entities: Tipos de entidades a anonimizar (opcional)
            
        Returns:
            Dict con texto anonimizado y estadísticas
        """
        if not text:
            return {"text": "", "items": []}
            
        # Analizar el texto primero
        analyzer_results = self.analyze_text(text, language, entities)
        
        # Convertir a formato esperado por el anonimizador
        analyzer_results_presidio = []
        
        for result in analyzer_results:
            # Crear RecognizerResult a partir del diccionario
            recognizer_result = RecognizerResult(
                entity_type=result["entity_type"],
                start=result["start"],
                end=result["end"],
                score=result["score"]
            )
            analyzer_results_presidio.append(recognizer_result)
            
        # Configurar operadores de anonimización según tipo de entidad
        operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTADO]"}),
            "PERSON": OperatorConfig("replace", {"new_value": "[NOMBRE]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[UBICACIÓN]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[TELÉFONO]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[TARJETA]"}),
            "COLOMBIAN_ID": OperatorConfig("replace", {"new_value": "[ID]"}),
            "IBAN_CODE": OperatorConfig("replace", {"new_value": "[CUENTA]"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "[FECHA]"}),
            "NRP": OperatorConfig("replace", {"new_value": "[ORGANIZACIÓN]"}),
            "US_PASSPORT": OperatorConfig("replace", {"new_value": "[PASAPORTE]"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "[SSN]"}),
            "US_DRIVER_LICENSE": OperatorConfig("replace", {"new_value": "[LICENCIA]"}),
        }
        
        # Realizar la anonimización
        try:
            anonymization_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results_presidio,
                operators=operators
            )
            
            self.logger.info(f"Texto anonimizado con {len(analyzer_results)} reemplazos")
            return {
                "text": anonymization_result.text,
                "items": [
                    {
                        "entity_type": item.entity_type,
                        "start": item.start,
                        "end": item.end,
                        "text": text[item.start:item.end],
                        "operator": item.operator
                    }
                    for item in anonymization_result.items
                ]
            }
        except Exception as e:
            self.logger.error(f"Error durante la anonimización: {str(e)}")
            return {"text": text, "items": [], "error": str(e)}
