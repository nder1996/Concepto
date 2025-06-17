from typing import List, Dict, Any, Tuple, Optional
import flair
from flair.data import Sentence
from flair.models import SequenceTagger
import re
import spacy
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flair_validator")

class FlairContextValidator:
    """    Validador contextual que utiliza Flair para refinar la detección de nombres de personas
    y reducir falsos positivos en español.
    
    Este validador actúa como una segunda capa después del análisis inicial de Presidio
    para mejorar la precisión en la detección de nombres propios.
    """
    
    def __init__(self, modelo_flair: str = "flair/ner-spanish-large", umbral_confianza: float = 0.90):
        """
        Inicializa el validador con un modelo de Flair.
        
        Args:
            modelo_flair: Nombre del modelo de Flair a utilizar
            umbral_confianza: Umbral mínimo de confianza para aceptar entidades detectadas (0.90 para alta precisión)
        """
        self.logger = logger
        self.umbral_confianza = umbral_confianza
        self.logger.info(f"Inicializando FlairContextValidator con modelo: {modelo_flair}")
        
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
            Dict con los resultados de la validación: 
            {
                "es_valido": bool,  # True si es un nombre válido
                "confianza": float,  # Puntuación de confianza
                "motivo": str,      # Razón de la decisión (si no es válido)
                "nombre_normalizado": str,  # Nombre normalizado (si es válido)
                "entidad_flair": Dict  # Detalles de la entidad Flair (si se detectó)
            }
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
                    if (texto_entidad in nombre or nombre in texto_entidad or
                        self._calcular_coincidencia(texto_entidad, nombre) > 0.7):
                        entidad_relacionada = {
                            "texto": texto_entidad,
                            "confianza": entidad.score,
                            "tag": entidad.tag
                        }
                        self.logger.info(f"Entidad Flair relacionada: {entidad.text} (score: {entidad.score:.4f})")
                        break
                        
            # Si no se encontró ninguna entidad de tipo PER que coincida
            if not entidad_relacionada:
                resultado["motivo"] = "No reconocido como PER por Flair"
                # Verificar si es una palabra común con análisis spaCy adicional
                doc = self.nlp(nombre)
                if any(token.pos_ in ['PROPN'] for token in doc):
                    self.logger.info(f"Posible nombre propio según spaCy, pero no validado por Flair")
                else:
                    self.logger.info(f"No detectado como nombre propio ni por Flair ni por spaCy")
                return resultado
                
            # 2. Validar según la confianza del modelo Flair
            if entidad_relacionada["confianza"] >= self.umbral_confianza:
                resultado["es_valido"] = True
                resultado["confianza"] = entidad_relacionada["confianza"]
                resultado["motivo"] = "Validado por Flair con alta confianza"
                resultado["entidad_flair"] = entidad_relacionada
                
                # Normalizar el nombre si es posible (usamos la versión detectada por Flair
                # si es más completa que la original)
                if len(entidad_relacionada["texto"]) > len(nombre) and nombre in entidad_relacionada["texto"]:
                    resultado["nombre_normalizado"] = entidad_relacionada["texto"]
                
                self.logger.info(f"Nombre VALIDADO: '{nombre}' con confianza {resultado['confianza']:.4f}")
                
            else:
                resultado["confianza"] = entidad_relacionada["confianza"]
                resultado["motivo"] = f"Confianza insuficiente en Flair ({entidad_relacionada['confianza']:.4f})"
                resultado["entidad_flair"] = entidad_relacionada
                self.logger.info(f"Nombre RECHAZADO por baja confianza: {entidad_relacionada['confianza']:.4f} < {self.umbral_confianza}")
            
        except Exception as e:
            self.logger.error(f"Error durante la validación con Flair: {str(e)}")
            resultado["motivo"] = f"Error en procesamiento: {str(e)}"
            
        return resultado
        
    def validar_listado_nombres(self, texto: str, candidatos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Procesa una lista de candidatos a nombres y devuelve solo aquellos que pasaron la validación de Flair.
        
        Args:
            texto: Texto completo original
            candidatos: Lista de diccionarios con los candidatos a validar
                        [{
                            "nombre": str,  # Texto del nombre
                            "start": int,   # Posición inicial
                            "end": int,     # Posición final
                            "confianza": float,  # Confianza original
                            "contexto": str  # Texto de contexto
                        }, ...]
                        
        Returns:
            Lista de candidatos validados con datos adicionales de la validación
        """
        self.logger.info(f"Validando {len(candidatos)} candidatos a nombres con Flair")
        validados = []
        
        for candidato in candidatos:
            nombre = candidato["nombre"]
            start = candidato["start"]
            end = candidato["end"]
            contexto = candidato.get("contexto", texto[max(0, start-50):min(len(texto), end+50)])
            
            # Aplicar validación con Flair
            resultado_validacion = self.validar_nombre(texto, nombre, contexto, start, end)
            
            # Si es válido según Flair, lo añadimos a la lista de validados
            if resultado_validacion["es_valido"]:
                # Combinar el candidato original con datos de la validación
                candidato_validado = {**candidato}
                candidato_validado["validado_flair"] = True
                candidato_validado["confianza_flair"] = resultado_validacion["confianza"]
                candidato_validado["nombre_normalizado"] = resultado_validacion["nombre_normalizado"]
                
                # Ajustar la confianza final (podemos combinar la original con la de Flair)
                # Damos más peso a la validación de Flair ya que es más específica para nombres
                candidato_validado["confianza_final"] = 0.3 * candidato["confianza"] + 0.7 * resultado_validacion["confianza"]
                
                validados.append(candidato_validado)
            else:
                self.logger.info(f"Candidato '{nombre}' rechazado: {resultado_validacion['motivo']}")
        
        self.logger.info(f"Validación completada: {len(validados)}/{len(candidatos)} candidatos validados")
        return validados
    
    def _calcular_coincidencia(self, texto1: str, texto2: str) -> float:
        """
        Calcula una puntuación de coincidencia entre dos textos.
        
        Args:
            texto1: Primer texto a comparar
            texto2: Segundo texto a comparar
            
        Returns:
            Puntuación de coincidencia entre 0 y 1
        """
        # Normalizar textos para comparación
        texto1 = texto1.lower()
        texto2 = texto2.lower()
        
        # Si uno está contenido en el otro, es una coincidencia alta
        if texto1 in texto2:
            return len(texto1) / len(texto2)
        if texto2 in texto1:
            return len(texto2) / len(texto1)
        
        # Dividir en palabras y verificar coincidencias
        palabras1 = set(texto1.split())
        palabras2 = set(texto2.split())
        
        # Calcular intersección de palabras
        palabras_comunes = palabras1.intersection(palabras2)
        
        # Calcular Jaccard Index para medida de similaridad
        if not palabras1 or not palabras2:
            return 0.0
            
        return len(palabras_comunes) / len(palabras1.union(palabras2))
