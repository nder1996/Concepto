from flask import Flask
from src.controllers.presidio_controller import PresidioController
from src.services.presidio.core_presidio_service import CorePresidioService
from src.services.file_processor import FileProcessor
from src.services.flair.flair_service import FlairService
from src.services.presidio_orchestrator_service import PresidioOrchestratorService
from src.utils.logger import setup_logger

def create_app():
    app = Flask(__name__)
    # Setup logger
    logger = setup_logger()
    logger.info("Iniciando aplicación Presidio API con soporte multilingüe (EN/ES) - Versión Core v3.1")
    
    # Inicializar el servicio de Flair (opcional)
    try:
        flair_service = FlairService()
        logger.info("Servicio Flair inicializado correctamente")
    except Exception as e:
        logger.warning(f"No se pudo inicializar Flair: {str(e)}. Se usará solo Presidio.")
        flair_service = None
    
    # Inicializar servicios
    entity_service = CorePresidioService(flair_service=flair_service)
    file_processor = FileProcessor()
    
    # Crear el servicio orquestador intermedio
    orchestrator_service = PresidioOrchestratorService(entity_service, file_processor, logger)
    
    # Initialize controller with orchestrator service
    controller = PresidioController(orchestrator_service, logger)
    
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
