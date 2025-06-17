import logging

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Configura y retorna un logger"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name)