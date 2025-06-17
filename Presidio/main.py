from flask import Flask
from src.controllers.api_controller import ApiController
from src.services.file_service import FileService
from src.services.anonymization_service import AnonymizationService
from src.presidio.engine import PresidioEngine
from src.utils.logger import setup_logger

def create_app():
    app = Flask(__name__)
    
    # Setup logger
    logger = setup_logger()
    logger.info("Iniciando aplicación Presidio API con soporte multilingüe (EN/ES)")
    
    # Initialize core engine
    presidio_engine = PresidioEngine()
    
    # Initialize services
    file_service = FileService()
    anonymization_service = AnonymizationService(presidio_engine, file_service)
    
    # Initialize controller
    controller = ApiController(anonymization_service, logger)
    
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