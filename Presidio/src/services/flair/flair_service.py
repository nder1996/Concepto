from typing import List, Dict, Any, Tuple, Optional
import flair
from flair.data import Sentence
from flair.models import SequenceTagger
import re
import spacy
import logging
from src.utils.logger import setup_logger
from src.config.settings import FLAIR_MODEL, FLAIR_CONFIDENCE_THRESHOLD

class FlairService:
    """
    Servicio para validación de entidades usando Flair.
    
    Proporciona funcionalidades para validar EXCLUSIVAMENTE entidades de tipo persona
    usando modelos de Flair para aumentar la precisión en la detección.
    """
    
    def __init__(self, modelo_flair: str = FLAIR_MODEL, umbral_confianza: float = FLAIR_CONFIDENCE_THRESHOLD):
        """
        Inicializa el servicio con un modelo de Flair.
        
        Args:
            modelo_flair: Nombre del modelo de Flair a utilizar
            umbral_confianza: Umbral mínimo de confianza para aceptar entidades detectadas
        """
        self.logger = setup_logger("FlairService")
        self.umbral_confianza = umbral_confianza
        self.logger.info(f"Inicializando FlairService con modelo: {modelo_flair}")
        
        try:
            # Cargar el modelo de Flair para español
            self.logger.info("Cargando modelo de Flair...")
            self.tagger = SequenceTagger.load(modelo_flair)
            self.logger.info("Modelo de Flair cargado correctamente")
            
            # Cargar spaCy para análisis de contexto adicional
            self.logger.info("Cargando modelo de spaCy para análisis auxiliar...")
            try:
                self.nlp = spacy.load("es_core_news_md")  # Preferible modelo mediano o grande
            except:
                self.nlp = spacy.load("es_core_news_sm")  # Fallback al modelo pequeño
            self.logger.info("Modelo de spaCy cargado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error al cargar los modelos: {str(e)}")
            raise
    
    def validar_nombre(self, texto: str, nombre: str, contexto: str, 
                       start: int, end: int) -> Dict[str, Any]:
        """
        Valida si un candidato identificado como nombre de persona es realmente un nombre
        utilizando el modelo Flair y análisis contextual.
        
        Args:
            texto: Texto completo original
            nombre: Nombre candidato a validar
            contexto: Contexto cercano al nombre (fragmento de texto que lo contiene)
            start: Posición de inicio del nombre en el texto original
            end: Posición de fin del nombre en el texto original
            
        Returns:
            Dict con los resultados de la validación
        """
        self.logger.info(f"Validando nombre: '{nombre}' (posición {start}-{end})")
        
        # Resultado por defecto (asumimos que no es válido hasta demostrar lo contrario)
        resultado = {
            "es_valido": False,
            "confianza": 0.0,
            "motivo": "No validado por Flair",
            "nombre_normalizado": nombre,
            "entidad_flair": None
        }
        
        # 1. Preparar el contexto para análisis con Flair
        try:
            # Usamos el contexto para aprovechar el análisis del modelo con mayor información
            sentence = Sentence(contexto)
            
            # Ejecutar el modelo Flair sobre la frase
            self.tagger.predict(sentence)
            
            # Buscar si alguna de las entidades detectadas por Flair coincide con nuestro candidato
            entidad_relacionada = None
            
            for entidad in sentence.get_spans('ner'):
                # Si la entidad es de tipo PER (persona)
                if entidad.tag == 'PER':
                    texto_entidad = entidad.text
                    # Verificar si hay solapamiento sustancial entre el nombre y la entidad detectada
                    if (nombre.lower() in texto_entidad.lower() or 
                        texto_entidad.lower() in nombre.lower() or
                        self._calcular_similaridad(nombre, texto_entidad) > 0.7):
                        
                        self.logger.info(f"Entidad Flair encontrada: '{texto_entidad}' ({entidad.score:.4f})")
                        
                        # Si hay múltiples coincidencias, quedarse con la de mayor puntuación
                        if (entidad_relacionada is None or 
                            entidad.score > entidad_relacionada.score):
                            entidad_relacionada = entidad
            
            # 2. Si Flair encontró una entidad relacionada con buena puntuación, es un nombre válido
            if entidad_relacionada and entidad_relacionada.score >= self.umbral_confianza:
                self.logger.info(f"Nombre VALIDADO por Flair con confianza: {entidad_relacionada.score:.4f}")
                
                resultado = {
                    "es_valido": True,
                    "confianza": entidad_relacionada.score,
                    "motivo": "Validado por Flair",
                    "nombre_normalizado": self._normalizar_nombre(entidad_relacionada.text),
                    "entidad_flair": {
                        "texto": entidad_relacionada.text,
                        "score": entidad_relacionada.score,
                        "tag": entidad_relacionada.tag
                    }
                }
                
                # Aplicar ajuste para corregir posiciones en el texto original si es necesario
                if self._necesita_ajuste_posicion(nombre, entidad_relacionada.text):
                    resultado["start"] = start
                    resultado["end"] = end
                    resultado["posiciones_ajustadas"] = True
            
            # 3. Si Flair encontró una entidad pero con baja puntuación
            elif entidad_relacionada:
                self.logger.info(f"Nombre RECHAZADO por Flair. Confianza insuficiente: {entidad_relacionada.score:.4f}")
                resultado["motivo"] = f"Confianza insuficiente: {entidad_relacionada.score:.4f}"
                resultado["confianza"] = entidad_relacionada.score
                resultado["entidad_flair"] = {
                    "texto": entidad_relacionada.text,
                    "score": entidad_relacionada.score,
                    "tag": entidad_relacionada.tag
                }
                
            # 4. Si Flair no encontró ninguna entidad PER relacionada
            else:
                self.logger.info(f"Nombre RECHAZADO: No detectado por Flair como entidad PER")
                resultado["motivo"] = "No identificado como persona por Flair"
        
        except Exception as e:
            self.logger.error(f"Error durante la validación con Flair: {str(e)}")
            resultado["motivo"] = f"Error en validación: {str(e)}"
            
        return resultado
    
    def validate_entity(self, entity_text: str, language: str, entity_type: str) -> bool:
        """
        Valida si una entidad detectada es de tipo PERSON usando el modelo Flair.
        Esta función solo validará entidades de tipo PERSON y rechazará las demás.
        
        Args:
            entity_text: El texto de la entidad a validar
            language: El idioma del texto ('es', 'en')
            entity_type: El tipo de entidad según Presidio
            
        Returns:
            bool: True si la entidad es válida como PERSON, False en caso contrario
        """
        # Solo procesar entidades de tipo PERSON
        if entity_type != "PERSON":
            self.logger.info(f"Tipo de entidad '{entity_type}' ignorada por Flair (solo valida PERSON)")
            return False
            
        # Extraer solo el texto de la entidad para análisis
        try:
            # Convertir a sentence para Flair
            sentence = Sentence(entity_text)
            
            # Aplicar el modelo
            self.tagger.predict(sentence)
            
            # Buscar si hay alguna entidad PER (persona) en las entidades detectadas
            for entity in sentence.get_spans('ner'):
                if entity.tag == 'PER' and entity.score > self.umbral_confianza:
                    self.logger.info(f"Entidad validada como PERSON por Flair con confianza: {entity.score:.4f}")
                    return True
                    
            self.logger.info(f"Entidad no validada como PERSON por Flair")
            return False
            
        except Exception as e:
            self.logger.error(f"Error al validar entidad con Flair: {str(e)}")
            return False
    
    # Métodos auxiliares internos
    def _calcular_similaridad(self, texto1: str, texto2: str) -> float:
        """Calcula la similitud entre dos textos usando una métrica simple"""
        texto1 = texto1.lower()
        texto2 = texto2.lower()
        
        # Si uno está contenido en el otro
        if texto1 in texto2 or texto2 in texto1:
            return 0.9
        
        # Comparar tokens (palabras)
        tokens1 = set(texto1.split())
        tokens2 = set(texto2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
            
        # Calcular similitud Jaccard
        interseccion = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return interseccion / union if union > 0 else 0.0
    
    def _normalizar_nombre(self, nombre: str) -> str:
        """Normaliza un nombre eliminando caracteres extraños y formateando correctamente"""
        nombre = nombre.strip()
        
        # Eliminar caracteres no alfabéticos al inicio o final
        nombre = re.sub(r'^[^a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]+|[^a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]+$', '', nombre)
        
        # Asegurar que cada parte del nombre empieza con mayúscula
        partes = nombre.split()
        partes_normalizadas = []
        
        for parte in partes:
            # Ignorar artículos y preposiciones en minúscula
            if parte.lower() in ['de', 'del', 'la', 'las', 'los', 'el']:
                partes_normalizadas.append(parte.lower())
            else:
                # Capitalizar la primera letra y mantener el resto como está
                if parte:
                    partes_normalizadas.append(parte[0].upper() + parte[1:])
        
        return ' '.join(partes_normalizadas)
        
    def _necesita_ajuste_posicion(self, nombre_original: str, nombre_flair: str) -> bool:
        """Determina si es necesario ajustar las posiciones por diferencias entre detecciones"""
        # Si son casi idénticos, no necesitamos ajuste
        if nombre_original.lower() == nombre_flair.lower():
            return False
        
        # Si hay una diferencia significativa (>20% de longitud), mejor mantener posiciones originales
        diff_len = abs(len(nombre_original) - len(nombre_flair))
        if diff_len > 0.2 * max(len(nombre_original), len(nombre_flair)):
            return True
            
        return False
