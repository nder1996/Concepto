import logging
import sys

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Configura y retorna un logger"""
    # Configuración para asegurar que los logs aparezcan en Docker
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Eliminar handlers existentes para evitar duplicados
    if logger.handlers:
        logger.handlers.clear()
        
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger