#!/usr/bin/env python
"""
Script de diagnóstico para probar reconocedores específicos en Presidio.
Este script permite probar los reconocedores de una manera aislada y controlada
para detectar problemas específicos.
"""

import sys
import os
import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Asegurarse de que podemos importar los módulos del proyecto
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from src.utils.custom_recognizers import register_custom_recognizers
from src.utils.logger import setup_logger

def test_location_recognizer(text, language='es'):
    """
    Función específica para diagnosticar problemas con el reconocedor de ubicaciones.
    
    Args:
        text (str): Texto para analizar
        language (str): Idioma del texto (default: 'es')
    """
    logger = setup_logger("LocationDiagnostics")
    logger.info(f"Iniciando diagnóstico de reconocedor de LOCATION")
    logger.info(f"Texto a analizar: {text}")
    logger.info(f"Idioma: {language}")
    
    # Configuración del motor NLP según el idioma
    model_name = "es_core_news_md" if language == "es" else "en_core_web_lg"
    logger.info(f"Usando modelo de SpaCy: {model_name}")
    
    try:
        # Configurar NLP Engine con el modelo correspondiente
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": language, "model_name": model_name}]
        })
        nlp_engine = provider.create_engine()
        
        # Crear y registrar reconocedores
        registry = RecognizerRegistry()
        register_custom_recognizers(registry)
        
        # Obtener lista de reconocedores registrados
        recognizers = registry.get_recognizers(language=language)
        logger.info(f"Reconocedores registrados para {language}: {len(recognizers)}")
        for r in recognizers:
            logger.info(f"  - {r.__class__.__name__}")
        
        # Crear analizador
        analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
        logger.info(f"Analizador inicializado correctamente")
        
        # Obtener entidades con umbral bajo para ver todos los resultados potenciales
        results = analyzer.analyze(text=text, language=language, entities=["LOCATION"], score_threshold=0.0)
        
        # Mostrar resultados detallados
        logger.info(f"Total de ubicaciones detectadas (incluye todas con umbral 0): {len(results)}")
        
        if not results:
            logger.warning("⚠️ No se detectaron ubicaciones en el texto")
            
            # Analizar directamente con SpaCy para ver qué etiquetas se asignan
            logger.info("Analizando directamente con SpaCy:")
            doc = nlp_engine.process_text(text, language)
            for ent in doc.entities:
                logger.info(f"  - Entidad SpaCy: {ent.text} → Tipo: {ent.entity_type}")
                
            # Mostrar todos los tokens para diagnóstico
            logger.info("Análisis token por token:")
            for token in doc.tokens:
                logger.info(f"  - Token: '{token.text}' → POS: {token.part_of_speech}, Tag: {token.tag}")
                
        else:
            for r in results:
                logger.info(f"Ubicación detectada: '{text[r.start:r.end]}'")
                logger.info(f"  - Score: {r.score}")
                logger.info(f"  - Posición: {r.start}-{r.end}")
                
    except Exception as e:
        logger.error(f"Error en diagnóstico: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Si no se proporciona texto, usamos un ejemplo
    text = sys.argv[1] if len(sys.argv) > 1 else "Vivo en Bogotá, Colombia y trabajo en Medellín"
    language = sys.argv[2] if len(sys.argv) > 2 else "es"
    
    test_location_recognizer(text, language)
