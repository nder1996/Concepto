from flask import Flask
from src.controllers.presidio_controller import PresidioController
from src.services.presidio_service import PresidioService
from src.services.file_processor import FileProcessor
from src.utils.logger import setup_logger

def create_app():
    app = Flask(__name__)
    
    # Setup logger
    logger = setup_logger()
    logger.info("Iniciando aplicación Presidio API con soporte multilingüe (EN/ES)")
    
    # Initialize services
    presidio_service = PresidioService()
    file_processor = FileProcessor()
    
    # Initialize controller
    controller = PresidioController(presidio_service, file_processor, logger)
    
    # Register routes
    controller.register_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    # En Docker configuramos para que los logs vayan a stdout
    import os
    is_docker = os.environ.get('RUNNING_IN_DOCKER', False)
    debug_mode = not is_docker  # Desactivar debug mode en Docker para no interferir con los logs
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)