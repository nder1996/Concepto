"""
Script para ejecutar la aplicación en modo debug local
"""
import logging
from main import create_app
from src.utils.logger import setup_logger

if __name__ == '__main__':
    # Configurar el logger para mostrar logs de nivel DEBUG
    logger = setup_logger("DebugLocal", logging.DEBUG)
    logger.info("Iniciando aplicación en modo DEBUG local")
    
    # Crear y ejecutar la aplicación en modo debug
    app = create_app()
    
    # En modo local, asegúrate de que debug=True para ver mensajes de error detallados
    app.run(host='localhost', port=5000, debug=True)
