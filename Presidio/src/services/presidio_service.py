from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict, Any
import spacy
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.utils.logger import setup_logger

# Importar los reconocedores personalizados
from src.services.recognizers.recognizer_email import EmailRecognizer
from src.services.recognizers.recognizer_phone import PhoneRecognizer
from src.services.recognizers.recognizer_co_identity_number import ColombianIDRecognizer

# Intentar importar el validador Flair (opcional)
try:
    from src.services.recognizers.flair_validator import FlairContextValidator
    FLAIR_DISPONIBLE = True
except ImportError:
    FLAIR_DISPONIBLE = False


class PresidioService:
    def __init__(self):
        # Inicializar los modelos de spaCy para diferentes idiomas
        self.logger = setup_logger("PresidioService")
        self.logger.info("Inicializando modelos de spaCy...")

        # Configurar motores NLP para cada idioma soportado
        self.nlp_engines = {}
        try:
            # Cargar el modelo de spaCy para español
            self.logger.info("Cargando modelo es_core_news_sm para español...")
            nlp_es = spacy.load("es_core_news_sm")
            nlp_config_es = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "es", "model_name": "es_core_news_sm"}],
            }
            nlp_provider_es = NlpEngineProvider(nlp_configuration=nlp_config_es)
            nlp_engine_es = nlp_provider_es.create_engine()

            # Cargar el modelo de spaCy para inglés
            self.logger.info("Cargando modelo en_core_web_sm para inglés...")
            nlp_en = spacy.load("en_core_web_sm")
            nlp_config_en = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            nlp_provider_en = NlpEngineProvider(nlp_configuration=nlp_config_en)
            nlp_engine_en = nlp_provider_en.create_engine()

            # Crear un registro de reconocedores para cada idioma
            self.logger.info("Configurando registros de reconocedores por idioma...")
            # Para español
            registry_es = RecognizerRegistry()
            registry_es.load_predefined_recognizers(nlp_engine=nlp_engine_es)

            # Registrar reconocedor personalizado de correo electrónico para español
            self.logger.info(
                "Registrando reconocedor personalizado de correos electrónicos para español..."
            )
            email_recognizer_es = EmailRecognizer(supported_language="es")
            registry_es.add_recognizer(email_recognizer_es)
            # Registrar reconocedor personalizado de teléfono para español
            self.logger.info(
                "Registrando reconocedor personalizado de números telefónicos para español..."
            )
            phone_recognizer_es = PhoneRecognizer(supported_language="es")
            registry_es.add_recognizer(phone_recognizer_es)
            # Registrar reconocedor personalizado de documentos de identidad colombianos (solo para español)
            self.logger.info(
                "Registrando reconocedor personalizado de documentos de identidad colombianos..."
            )
            id_recognizer_es = ColombianIDRecognizer(supported_language="es")
            registry_es.add_recognizer(id_recognizer_es)            # Usar el reconocedor predeterminado de Presidio para nombres de personas
            self.logger.info(
                "Usando reconocedor predeterminado de Presidio para nombres de personas en español..."
            )

            # Registrar mensajes informativos sobre los tipos de documentos soportados
            self.logger.info(
                "Reconocedor de documentos de identidad colombianos configurado con los siguientes tipos:"
            )
            self.logger.info("- Cédula de Ciudadanía (CC)")
            self.logger.info("- Tarjeta de Identidad (TI)")
            self.logger.info("- Cédula de Extranjería (CE)")
            self.logger.info("- Registro Civil (RC)")
            self.logger.info("- Pasaporte (PA)")
            self.logger.info("- NIT")
            self.logger.info("- Permiso Especial de Permanencia (PEP)")

            self.analyzer_es = AnalyzerEngine(
                registry=registry_es, nlp_engine=nlp_engine_es
            )

            # Para inglés
            registry_en = RecognizerRegistry()
            registry_en.load_predefined_recognizers(nlp_engine=nlp_engine_en)

            # Registrar reconocedor personalizado de correo electrónico para inglés
            self.logger.info(
                "Registrando reconocedor personalizado de correos electrónicos para inglés..."
            )
            email_recognizer_en = EmailRecognizer(supported_language="en")
            registry_en.add_recognizer(email_recognizer_en)

            # Registrar reconocedor personalizado de teléfono para inglés
            self.logger.info(
                "Registrando reconocedor personalizado de números telefónicos para inglés..."
            )
            phone_recognizer_en = PhoneRecognizer(supported_language="en")
            registry_en.add_recognizer(phone_recognizer_en)            # Usar el reconocedor predeterminado de Presidio para nombres de personas
            self.logger.info(
                "Usando reconocedor predeterminado de Presidio para nombres de personas en inglés..."
            )

            self.analyzer_en = AnalyzerEngine(
                registry=registry_en, nlp_engine=nlp_engine_en
            )

            self.analyzers = {"es": self.analyzer_es, "en": self.analyzer_en}

            self.logger.info(
                "Motores de análisis inicializados correctamente para todos los idiomas."
            )
        except Exception as e:
            self.logger.error(f"Error al inicializar los motores de análisis: {str(e)}")
            raise

        # Inicializar el motor de anonimización
        self.anonymizer = AnonymizerEngine()

        # Idiomas soportados
        self.supported_languages = ["en", "es"]
        self.default_language = "es"

        # Registrar la inicialización
        self.logger.info(
            f"Servicio Presidio inicializado con soporte para idiomas: {', '.join(self.supported_languages)}"
        )        # Entidades específicas a considerar (comunes a todos los idiomas)
        self.target_entities = [
            "PERSON",  # Nombres de personas (usando reconocedor personalizado)
            "PHONE_NUMBER",
            # "LOCATION",
            # "DATE_TIME",
            "EMAIL_ADDRESS",
            # Documentos de identidad colombianos y sus tipos específicos
            "CO_ID_NUMBER",  # Documento genérico
            "CO_ID_NUMBER_CC",  # Cédula de ciudadanía
            "CO_ID_NUMBER_TI",  # Tarjeta de identidad
            "CO_ID_NUMBER_CE",  # Cédula de extranjería
            "CO_ID_NUMBER_RC",  # Registro civil
            "CO_ID_NUMBER_PA",  # Pasaporte
            "CO_ID_NUMBER_NIT",  # NIT
            "CO_ID_NUMBER_PEP",  # Permiso Especial de Permanencia
        ]
        
        # Umbrales específicos para cada tipo de entidad - configuración para inglés
        self.entity_thresholds_en = {
            "PERSON": 0.1,  # Umbral bajo para capturar más candidatos que luego serán validados por Flair
            "PHONE_NUMBER": 0.3,  # Bajamos a 0.3 para mejorar detección de teléfonos
            # "LOCATION": 0.80,
            # "DATE_TIME": 0.70,
            "EMAIL_ADDRESS": 0.6,  # Ajustado para trabajar mejor con nuestro reconocedor personalizado
            # Documentos de identidad colombianos
            "CO_ID_NUMBER": 0.65,  # Umbral base para documentos de identidad colombianos
            "CO_ID_NUMBER_CC": 0.60,  # Cédula de ciudadanía - más común, podemos bajar umbral
            "CO_ID_NUMBER_TI": 0.65,  # Tarjeta de identidad
            "CO_ID_NUMBER_CE": 0.65,  # Cédula de extranjería
            "CO_ID_NUMBER_RC": 0.65,  # Registro civil
            "CO_ID_NUMBER_PA": 0.70,  # Pasaporte - formato más específico
            "CO_ID_NUMBER_NIT": 0.70,  # NIT - formato más específico
            "CO_ID_NUMBER_PEP": 0.70,  # Permiso Especial de Permanencia
        }
          # Umbrales específicos para cada tipo de entidad - configuración para español
        # Ajustamos los umbrales para mejorar la precisión en español
        self.entity_thresholds_es = {
            "PERSON": 0.1,  # Umbral bajo para capturar más candidatos que luego serán validados por Flair
            "PHONE_NUMBER": 0.3,  # Más bajo para detectar mejor los números en diferentes formatos
            # "LOCATION": 0.70,
            # "DATE_TIME": 0.65,
            "EMAIL_ADDRESS": 0.6,  # Ajustado para trabajar mejor con nuestro reconocedor personalizado
            # Documentos de identidad colombianos - umbrales más bajos en español para mejor detección
            "CO_ID_NUMBER": 0.5,  # Umbral base para documentos genéricos
            "CO_ID_NUMBER_CC": 0.45,  # Cédula de ciudadanía - formato muy común en Colombia
            "CO_ID_NUMBER_TI": 0.5,  # Tarjeta de identidad
            "CO_ID_NUMBER_CE": 0.5,  # Cédula de extranjería
            "CO_ID_NUMBER_RC": 0.5,  # Registro civil
            "CO_ID_NUMBER_PA": 0.6,  # Pasaporte
            "CO_ID_NUMBER_NIT": 0.6,  # NIT - formato comercial            "CO_ID_NUMBER_PEP": 0.6,  # Permiso Especial de Permanencia
        }
        
        # Diccionario de umbrales por idioma
        self.thresholds_by_language = {
            "en": self.entity_thresholds_en,
            "es": self.entity_thresholds_es,
        }

    def get_entity_thresholds(self, language: str) -> Dict[str, float]:
        """Obtiene los umbrales específicos para el idioma seleccionado"""
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando configuración predeterminada (inglés)."
            )
            return self.entity_thresholds_en
        return self.thresholds_by_language.get(language, self.entity_thresholds_en)
        
    def analyze_text(self, text: str, language: str = "es") -> List[Dict[str, Any]]:
        """Analiza texto y retorna solo las entidades específicas que superen el umbral configurado"""
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language

        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)

        # Log detallado para debug
        self.logger.info(f"Analizando texto: '{text[:50]}...' en idioma: {language}")
        self.logger.info(f"Umbrales aplicados para {language}: {thresholds}")
        
        # Primero, validar entidades de tipo PERSON usando el reconocedor personalizado
        person_entities = self.validate_person_entities(text, language)
        
        # Seleccionar el analizador específico para el idioma
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(
                f"No se encontró un analizador para el idioma: {language}"
            )
            return []

        # Analizar el texto con el analizador para las entidades que no son PERSON
        # ya que estas ya fueron procesadas con filtros específicos
        non_person_entities = [entity for entity in self.target_entities if entity != "PERSON"]
        results = analyzer.analyze(text=text, language=language, entities=non_person_entities)

        # Registrar todas las entidades detectadas originalmente
        self.logger.info(f"Total de entidades no-PERSON detectadas: {len(results)}")

        # Lista para almacenar todas las entidades filtradas
        filtered_results = []
        
        # Agregar las entidades PERSON ya validadas
        filtered_results.extend(person_entities)

        # Procesar otras entidades que no son PERSON
        for r in results:
            self.logger.info(
                f"Entidad detectada: {r.entity_type}, "
                f"Score: {r.score}, Texto: {text[r.start:r.end]}"
            )
            # Filtrar todas las entidades que superen el umbral
            if r.entity_type in self.target_entities and r.score >= thresholds.get(
                r.entity_type, 0.80
            ):
                filtered_results.append(
                    {
                        "entity_type": r.entity_type,
                        "start": r.start,
                        "end": r.end,
                        "score": r.score,
                        "language": language,
                    }
                )

        # Registrar las entidades que superan el filtro
        self.logger.info(
            f"Entidades que superan el umbral ({language}): {len(filtered_results)}"
        )
        for r in filtered_results:
            if "entity_type" in r:  # Asegurarse de que tiene la estructura correcta
                threshold = thresholds.get(r["entity_type"], 0.80)
                # Log detallado para diferentes tipos de entidades
                if r["entity_type"].startswith("CO_ID_NUMBER"):
                    doc_type = (
                        r["entity_type"].replace("CO_ID_NUMBER_", "")
                        if "_" in r["entity_type"]
                        else "GENÉRICO"
                    )
                    self.logger.info(
                        f"Documento colombiano detectado: {doc_type}, "
                        f"Score: {r['score']} (umbral: {threshold}), Texto: {text[r['start']:r['end']]}"
                    )
                elif r["entity_type"] == "PERSON":
                    self.logger.info(
                        f"Nombre de persona detectado: {text[r['start']:r['end']]}, "
                        f"Score: {r['score']} (umbral: {threshold})"
                    )
                else:
                    self.logger.info(
                        f"Entidad considerada: {r['entity_type']}, "
                        f"Score: {r['score']} (umbral: {threshold}), Texto: {text[r['start']:r['end']]}"
                    )

        return filtered_results

    def anonymize_text(self, text: str, language: str = "es") -> str:
        """Anonimiza texto reemplazando solo entidades específicas con puntaje superior al umbral"""
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language

        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)

        # Log detallado para debug
        self.logger.info(f"Anonimizando texto: '{text[:50]}...' en idioma: {language}")
        self.logger.info(f"Umbrales aplicados para {language}: {thresholds}")
        # Primero, validar entidades de tipo PERSON usando el reconocedor personalizado
        person_entities = self.validate_person_entities(text, language)
        # Convertir resultados de personas a formato RecognizerResult para el anonimizador
        person_recognizer_results = []
        for entity in person_entities:
            # Crear objetos RecognizerResult para cada nombre detectado
            person_result = RecognizerResult(
                entity_type=entity["entity_type"],
                start=entity["start"],
                end=entity["end"],
                score=entity["score"],
            )
            person_recognizer_results.append(person_result)

        # Seleccionar el analizador específico para el idioma para otras entidades
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(
                f"No se encontró un analizador para el idioma: {language}"
            )
            return text

        # Analizar el texto para otras entidades
        results = analyzer.analyze(text=text, language=language)

        # Registrar todas las entidades detectadas originalmente
        self.logger.info(f"Total de entidades detectadas (no-PERSON): {len(results)}")

        # Filtrar entidades que no son PERSON (ya procesadas por validate_person_entities)
        other_entities_results = []
        for r in results:
            if (
                r.entity_type != "PERSON"
                and r.entity_type in self.target_entities
                and r.score >= thresholds.get(r.entity_type, 0.80)
            ):
                self.logger.info(
                    f"Entidad detectada: {r.entity_type}, "
                    f"Score: {r.score}, Texto: {text[r.start:r.end]}"
                )
                other_entities_results.append(r)

        # Combinar resultados de entidades PERSON y otras entidades
        filtered_results = person_recognizer_results + other_entities_results
        # Registrar las entidades que SÍ serán anonimizadas
        self.logger.info(
            f"Entidades que serán anonimizadas ({language}): {len(filtered_results)}"
        )
        for r in filtered_results:
            threshold = thresholds.get(r.entity_type, 0.80)
            # Log detallado para diferentes tipos de entidades
            if r.entity_type.startswith("CO_ID_NUMBER"):
                doc_type = (
                    r.entity_type.replace("CO_ID_NUMBER_", "")
                    if "_" in r.entity_type
                    else "GENÉRICO"
                )
                self.logger.info(
                    f"Documento colombiano anonimizado: {doc_type}, "
                    f"Score: {r.score} (umbral: {threshold}), Texto: {text[r.start:r.end]}"
                )
            elif r.entity_type == "PERSON":
                self.logger.info(
                    f"Nombre de persona anonimizado: {text[r.start:r.end]}, "
                    f"Score: {r.score} (umbral: {threshold})"
                )
            else:
                self.logger.info(
                    f"Entidad anonimizada: {r.entity_type}, "
                    f"Score: {r.score} (umbral: {threshold}), Texto: {text[r.start:r.end]}"
                )        # Anonimizar solo las entidades filtradas
        anonymized = self.anonymizer.anonymize(
            text=text, analyzer_results=filtered_results
        )
        return anonymized.text
        
    def validate_person_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        """
        Valida las entidades de tipo PERSON utilizando el reconocedor predeterminado de Presidio
        y luego valida con Flair si realmente son nombres de persona.
        
        Args:
            text: Texto a analizar
            language: Idioma del texto (es, en)
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades validadas con información detallada
        """
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"            )
            language = self.default_language
            
        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)
        person_threshold = thresholds.get("PERSON", 0.1)  # Usar umbral de 0.1 para PERSON
        
        # Seleccionar el analizador específico para el idioma
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return []
            
        # Analizar el texto específicamente para entidades de tipo PERSON
        results = analyzer.analyze(text=text, language=language, entities=["PERSON"])
        
        # Registrar análisis inicial
        self.logger.info(f"Detectando nombres de personas en texto: '{text[:50]}...' en idioma: {language}")
        self.logger.info(f"Umbral aplicado para PERSON: {person_threshold}")
        self.logger.info(f"Total de nombres detectados inicialmente: {len(results)}")
        
        # Lista para almacenar entidades validadas
        validated_results = []
        
        # Lista para almacenar candidatos que pasan el umbral de Presidio y pueden ser validados por Flair
        candidatos_para_flair = []
        
        # Filtrar solo las entidades que superen el umbral configurado
        for r in results:
            if r.entity_type == "PERSON" and r.score >= person_threshold:
                name_text = text[r.start:r.end].strip()
                self.logger.info(f"Nombre detectado que supera umbral: '{name_text}', Score: {r.score}")
                
                # Extraer contexto para validación Flair
                inicio_contexto = max(0, r.start - 50)
                fin_contexto = min(len(text), r.end + 50)
                contexto = text[inicio_contexto:fin_contexto]
                
                # Añadir a candidatos para validación con Flair
                candidato = {
                    "entity_type": "PERSON",
                    "nombre": name_text,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "language": language,
                    "contexto": contexto
                }
                candidatos_para_flair.append(candidato)
        
        self.logger.info(f"Total de nombres que superan umbral de Presidio: {len(candidatos_para_flair)}")
        
        # Verificar si Flair está disponible
        if FLAIR_DISPONIBLE and candidatos_para_flair:
            self.logger.info("⭐ Aplicando validación con Flair...")
            try:
                # Crear una instancia del validador Flair si no existe
                validador_flair = FlairContextValidator()
                
                # Validar los candidatos con Flair
                for candidato in candidatos_para_flair:
                    nombre = candidato["nombre"]
                    contexto = candidato["contexto"]
                    start = candidato["start"]
                    end = candidato["end"]
                    
                    resultado_validacion = validador_flair.validar_nombre(
                        texto=text, 
                        nombre=nombre, 
                        contexto=contexto,
                        start=start, 
                        end=end
                    )
                    
                    if resultado_validacion["es_valido"]:
                        # Es un nombre válido según Flair
                        validated_results.append({
                            "entity_type": "PERSON",
                            "start": start,
                            "end": end,
                            "score": resultado_validacion["confianza"],
                            "language": language,
                        })
                        self.logger.info(f"✅ Nombre validado por Flair: '{resultado_validacion['nombre_normalizado']}', Score: {resultado_validacion['confianza']}")
                    else:
                        self.logger.info(f"❌ Descartado por Flair: '{nombre}' - Motivo: {resultado_validacion['motivo']}")
                
                self.logger.info(f"Total de nombres validados por Flair: {len(validated_results)}")
                
            except Exception as e:
                self.logger.error(f"Error en validación con Flair: {str(e)}")
                # Si falla Flair, usamos los candidatos que pasaron el umbral de Presidio
                self.logger.info("Usando candidatos que superaron el umbral de Presidio como fallback")
                for c in candidatos_para_flair:
                    validated_results.append({
                        "entity_type": c["entity_type"],
                        "start": c["start"],
                        "end": c["end"],
                        "score": c["score"],
                        "language": c["language"],
                    })
                    self.logger.info(f"✅ Nombre que superó umbral de Presidio (sin validación Flair): '{c['nombre']}', Score: {c['score']}")
        else:
            # Si no hay validador Flair disponible, usar los candidatos que pasaron el umbral de Presidio
            if not FLAIR_DISPONIBLE:
                self.logger.info("⚠️ Validador Flair no disponible")
            
            for c in candidatos_para_flair:
                validated_results.append({
                    "entity_type": c["entity_type"],
                    "start": c["start"],
                    "end": c["end"],
                    "score": c["score"],
                    "language": c["language"],
                })
                self.logger.info(f"✅ Nombre validado por umbral de Presidio: '{c['nombre']}', Score: {c['score']}")
        
        self.logger.info(f"Total de nombres validados después del proceso completo: {len(validated_results)}")
        return validated_results
  
