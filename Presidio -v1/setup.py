"""
Script para configurar el entorno e instalar los modelos de lenguaje necesarios.
Ejecutar después de instalar los requerimientos:

pip install -r requerimientos.txt
python setup.py
"""

import subprocess
import sys
import logging

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

def main():
    """Función principal de configuración"""
    logger.info("Iniciando configuración del entorno...")
    
    # Instalar modelos de spaCy
    if not install_spacy_models():
        logger.warning("No se pudieron instalar todos los modelos de spaCy")
    
    logger.info("Configuración completada.")

if __name__ == "__main__":
    main()
