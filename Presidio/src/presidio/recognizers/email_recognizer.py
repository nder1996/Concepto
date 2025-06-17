"""
Validador contextual usando Flair NLP para mejorar la detección de nombres de personas.

Este módulo utiliza Flair, una biblioteca de NLP avanzada, para validar si las entidades
detectadas como nombres de personas son realmente nombres en el contexto dado.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import logging

# Intentar importar Flair - es opcional
try:
    from flair.data import Sentence
    from flair.models import SequenceTagger
    FLAIR_AVAILABLE = True
except ImportError:
    FLAIR_AVAILABLE = False

# Configurar logger
logger = logging.getLogger("flair_validator")

class FlairContextValidator:
    """
    Validador contextual para nombres de personas usando Flair NLP.
    
    Esta clase utiliza modelos de Flair para validar si las entidades detectadas
    como nombres de personas son realmente nombres en el contexto específico.
    """
    
    def __init__(self, umbral_confianza: float = 0.7):
        """
        Inicializa el validador Flair.
        
        Args:
            umbral_confianza: Umbral mínimo de confianza para considerar válido un nombre
        """
        self.logger = logger
        self.umbral_confianza = umbral_confianza
        self.modelo_cargado = False
        self.tagger = None
        
        # Verificar si Flair está disponible
        if not FLAIR_AVAILABLE:
            self.logger.warning("Flair no está disponible. El validador funcionará en modo fallback.")
            return
        
        # Intentar cargar el modelo de Flair
        try:
            self._cargar_modelo()
        except Exception as e:
            self.logger.warning(f"No se pudo cargar el modelo de Flair: {str(e)}")
            self.logger.info("El validador funcionará en modo fallback sin Flair")
    
    def _cargar_modelo(self):
        """Carga el modelo de NER de Flair"""
        try:
            self.logger.info("Cargando modelo de Flair para NER...")
            # Intentar cargar el modelo multilingüe primero
            self.tagger = SequenceTagger.load('ner-multi')
            self.modelo_cargado = True
            self.logger.info("Modelo de Flair cargado exitosamente")
        except Exception as e:
            try:
                # Si falla el multilingüe, intentar el modelo en inglés
                self.logger.info("Intentando cargar modelo de Flair en inglés...")
                self.tagger = SequenceTagger.load('ner')
                self.modelo_cargado = True
                self.logger.info("Modelo de Flair en inglés cargado exitosamente")
            except Exception as e2:
                self.logger.error(f"No se pudo cargar ningún modelo de Flair: {str(e2)}")
                raise e2
    
    def validar_nombre(self, 
                      texto: str, 
                      nombre: str, 
                      contexto: str,
                      start: int = 0, 
                      end: int = 0) -> Dict[str, Any]:
        """
        Valida si un nombre detectado es realmente un nombre de persona.
        
        Args:
            texto: Texto completo donde se detectó el nombre
            nombre: Nombre detectado a validar
            contexto: Contexto alrededor del nombre
            start: Posición inicial del nombre en el texto
            end: Posición final del nombre en el texto
            
        Returns:
            Dict con información de validación:
            - es_valido: bool
            - confianza: float
            - motivo: str
            - nombre_normalizado: str
            - metodo_validacion: str
        """
        # Resultado por defecto
        resultado = {
            "es_valido": False,
            "confianza": 0.0,
            "motivo": "Validación no realizada",
            "nombre_normalizado": nombre.strip(),
            "metodo_validacion": "fallback"
        }
        
        # Validaciones básicas primero
        validacion_basica = self._validacion_basica(nombre)
        if not validacion_basica["es_valido"]:
            resultado.update(validacion_basica)
            return resultado
        
        # Si Flair está disponible, usar validación avanzada
        if self.modelo_cargado and FLAIR_AVAILABLE:
            try:
                resultado_flair = self._validar_con_flair(texto, nombre, contexto, start, end)
                resultado.update(resultado_flair)
                resultado["metodo_validacion"] = "flair"
            except Exception as e:
                self.logger.warning(f"Error en validación con Flair: {str(e)}")
                # Usar validación de reglas como fallback
                resultado_reglas = self._validacion_por_reglas(nombre, contexto)
                resultado.update(resultado_reglas)
                resultado["metodo_validacion"] = "reglas_fallback"
        else:
            # Usar validación por reglas
            resultado_reglas = self._validacion_por_reglas(nombre, contexto)
            resultado.update(resultado_reglas)
            resultado["metodo_validacion"] = "reglas"
        
        return resultado
    
    def _validacion_basica(self, nombre: str) -> Dict[str, Any]:
        """Realiza validaciones básicas del nombre"""
        nombre_limpio = nombre.strip()
        
        # Verificar que no esté vacío
        if not nombre_limpio:
            return {
                "es_valido": False,
                "confianza": 0.0,
                "motivo": "Nombre vacío"
            }
        
        # Verificar longitud mínima y máxima
        if len(nombre_limpio) < 2:
            return {
                "es_valido": False,
                "confianza": 0.0,
                "motivo": "Nombre demasiado corto"
            }
        
        if len(nombre_limpio) > 100:
            return {
                "es_valido": False,
                "confianza": 0.0,
                "motivo": "Nombre demasiado largo"
            }
        
        # Verificar que contenga principalmente letras
        letters_ratio = sum(c.isalpha() or c.isspace() for c in nombre_limpio) / len(nombre_limpio)
        if letters_ratio < 0.7:
            return {
                "es_valido": False,
                "confianza": 0.0,
                "motivo": "Contiene demasiados caracteres no alfabéticos"
            }
        
        # Rechazar palabras obvias que no son nombres
        palabras_no_nombres = {
            "usuario", "user", "admin", "administrador", "persona", "name", 
            "nombre", "example", "ejemplo", "test", "prueba", "cliente",
            "customer", "email", "correo", "telefono", "phone"
        }
        
        if nombre_limpio.lower() in palabras_no_nombres:
            return {
                "es_valido": False,
                "confianza": 0.0,
                "motivo": "Palabra común que no es nombre"
            }
        
        return {"es_valido": True, "confianza": 0.5, "motivo": "Pasó validaciones básicas"}
    
    def _validar_con_flair(self, 
                          texto: str, 
                          nombre: str, 
                          contexto: str,
                          start: int, 
                          end: int) -> Dict[str, Any]:
        """Valida usando el modelo de Flair"""
        try:
            # Crear una oración con el contexto para análisis
            oracion_contexto = Sentence(contexto)
            
            # Ejecutar el modelo de NER sobre el contexto
            self.tagger.predict(oracion_contexto)
            
            # Buscar entidades de tipo PERSON en los resultados
            nombres_encontrados = []
            for entidad in oracion_contexto.get_spans('ner'):
                if entidad.tag == 'PER' or entidad.tag == 'PERSON':
                    texto_entidad = entidad.text.strip()
                    confianza_entidad = entidad.score
                    
                    # Verificar si coincide con nuestro nombre (permitir coincidencias parciales)
                    if self._nombres_coinciden(nombre, texto_entidad):
                        nombres_encontrados.append({
                            "texto": texto_entidad,
                            "confianza": confianza_entidad,
                            "coincidencia": self._calcular_coincidencia(nombre, texto_entidad)
                        })
            
            # Evaluar resultados
            if nombres_encontrados:
                # Tomar la mejor coincidencia
                mejor_coincidencia = max(nombres_encontrados, key=lambda x: x["coincidencia"] * x["confianza"])
                
                confianza_final = mejor_coincidencia["confianza"] * mejor_coincidencia["coincidencia"]
                
                if confianza_final >= self.umbral_confianza:
                    return {
                        "es_valido": True,
                        "confianza": confianza_final,
                        "motivo": f"Confirmado por Flair (score: {confianza_final:.2f})",
                        "nombre_normalizado": mejor_coincidencia["texto"]
                    }
                else:
                    return {
                        "es_valido": False,
                        "confianza": confianza_final,
                        "motivo": f"Confianza de Flair insuficiente (score: {confianza_final:.2f})"
                    }
            else:
                # Flair no detectó el nombre como persona
                return {
                    "es_valido": False,
                    "confianza": 0.2,
                    "motivo": "Flair no identificó el texto como nombre de persona"
                }
                
        except Exception as e:
            self.logger.error(f"Error en validación con Flair: {str(e)}")
            raise e
    
    def _validacion_por_reglas(self, nombre: str, contexto: str) -> Dict[str, Any]:
        """Validación usando reglas heurísticas cuando Flair no está disponible"""
        nombre_limpio = nombre.strip()
        contexto_lower = contexto.lower()
        
        confianza = 0.5  # Confianza base
        motivos = []
        
        # Verificar estructura del nombre (palabras capitalizadas)
        palabras = nombre_limpio.split()
        if len(palabras) >= 2:
            palabras_capitalizadas = sum(1 for p in palabras if p[0].isupper() if len(p) > 0)
            if palabras_capitalizadas == len(palabras):
                confianza += 0.2
                motivos.append("nombres correctamente capitalizados")
        
        # Verificar contexto que indica nombres
        indicadores_nombre = [
            r"\bseñor[a]?\s+", r"\bsr[a]?\.\s+", r"\bdoctor[a]?\s+", r"\bdr[a]?\.\s+",
            r"\blic\.\s+", r"\bing\.\s+", r"\bprof\.\s+",
            r"\bmi\s+nombre\s+es\b", r"\bme\s+llamo\b", r"\bsoy\b",
            r"\bcompañer[oa]\s+", r"\bamig[oa]\s+", r"\bcoleg[a]\s+"
        ]
        
        for patron in indicadores_nombre:
            if re.search(patron, contexto_lower):
                confianza += 0.15
                motivos.append("contexto indica nombre de persona")
                break
        
        # Verificar patrones de nombres comunes en español
        patrones_nombres_es = [
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",  # Patrón nombre apellido
            r"\b[A-Z][a-z]*(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+\b"        # Patrón con inicial
        ]
        
        for patron in patrones_nombres_es:
            if re.match(patron, nombre_limpio):
                confianza += 0.1
                motivos.append("coincide con patrón de nombre típico")
                break
        
        # Penalizar si parece información técnica
        if re.search(r"\b(?:@|\.com|\.co|www|http|tel|phone|email)\b", contexto_lower):
            confianza -= 0.3
            motivos.append("contexto técnico detectado")
        
        # Penalizar si parece un documento
        if re.search(r"\b(?:cedula|cédula|documento|id|nit|cc|ce|ti)\b", contexto_lower):
            confianza -= 0.2
            motivos.append("contexto de documento detectado")
        
        # Determinar validez
        es_valido = confianza >= self.umbral_confianza
        motivo_final = "Validación por reglas: " + ", ".join(motivos) if motivos else "Sin indicadores claros"
        
        return {
            "es_valido": es_valido,
            "confianza": max(0.0, min(1.0, confianza)),
            "motivo": motivo_final
        }
    
    def _nombres_coinciden(self, nombre1: str, nombre2: str) -> bool:
        """Verifica si dos nombres coinciden (permitiendo variaciones)"""
        # Normalizar nombres
        n1 = re.sub(r'[^\w\s]', '', nombre1.lower()).strip()
        n2 = re.sub(r'[^\w\s]', '', nombre2.lower()).strip()
        
        # Coincidencia exacta
        if n1 == n2:
            return True
        
        # Verificar si uno contiene al otro (para nombres parciales)
        if n1 in n2 or n2 in n1:
            return True
        
        # Verificar coincidencia de palabras
        palabras1 = set(n1.split())
        palabras2 = set(n2.split())
        
        # Si al menos la mitad de las palabras coinciden
        if len(palabras1.intersection(palabras2)) >= max(1, min(len(palabras1), len(palabras2)) // 2):
            return True
        
        return False
    
    def _calcular_coincidencia(self, nombre1: str, nombre2: str) -> float:
        """Calcula el grado de coincidencia entre dos nombres (0.0 a 1.0)"""
        # Normalizar nombres
        n1 = re.sub(r'[^\w\s]', '', nombre1.lower()).strip()
        n2 = re.sub(r'[^\w\s]', '', nombre2.lower()).strip()
        
        # Coincidencia exacta
        if n1 == n2:
            return 1.0
        
        # Calcular coincidencia por palabras
        palabras1 = set(n1.split())
        palabras2 = set(n2.split())
        
        if not palabras1 or not palabras2:
            return 0.0
        
        interseccion = len(palabras1.intersection(palabras2))
        union = len(palabras1.union(palabras2))
        
        return interseccion / union if union > 0 else 0.0


class FlairContextValidator:
    """Alias para compatibilidad con código existente"""
    def __init__(self, umbral_confianza: float = 0.7):
        self.validator = FlairContextValidator(umbral_confianza)
    
    def validar_nombre(self, texto: str, nombre: str, contexto: str, start: int = 0, end: int = 0):
        return self.validator.validar_nombre(texto, nombre, contexto, start, end)