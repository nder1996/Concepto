"""
Script para configurar el entorno e instalar los modelos de lenguaje necesarios.
Ejecutar después de instalar los requerimientos:

pip install -r ../../requerimientos.txt
python setup.py
"""

import subprocess
import sys
import logging
import os

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('setup')

def install_spacy_models():
    """Instala los modelos de spaCy necesarios para español e inglés"""
    try:
        logger.info("Instalando modelo de spaCy para español (es_core_news_md)...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "es_core_news_md"])
        
        logger.info("Instalando modelo de spaCy para inglés (en_core_web_lg)...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_lg"])
        
        logger.info("Modelos de spaCy instalados correctamente!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al instalar modelos de spaCy: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return False

def validate_environment():
    """Valida que el entorno esté configurado correctamente"""
    logger.info("Validando configuración del entorno...")
    
    # Verificar si los archivos de configuración están presentes
    config_files = ["entity_config.py", "language_config.py"]
    for file in config_files:
        if not os.path.exists(os.path.join(os.path.dirname(__file__), file)):
            logger.error(f"Archivo de configuración {file} no encontrado")
            return False
    
    logger.info("Archivos de configuración validados correctamente")
    return True

def main():
    """Función principal de configuración"""
    logger.info("Iniciando configuración del entorno...")
    
    # Validar entorno
    if not validate_environment():
        logger.error("La validación del entorno falló. Revise los archivos de configuración.")
        return False
    
    # Instalar modelos de spaCy
    if not install_spacy_models():
        logger.warning("No se pudieron instalar todos los modelos de spaCy")
    
    logger.info("Configuración completada.")
    return True

if __name__ == "__main__":
    main()
