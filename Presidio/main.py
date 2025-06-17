from flask import Flask
from src.controllers.presidio_controller import PresidioController
from src.services.presidio.core_presidio_service import CorePresidioService
from src.services.file_processor import FileProcessor
from src.services.flair.flair_service import FlairService
from src.services.presidio_orchestrator_service import PresidioOrchestratorService
from src.utils.logger import setup_logger


def create_app():
    app = Flask(__name__)
    logger = setup_logger()

    # Crear servicio Flair (sin cargar modelo)
    flair_service = None
    try:
        flair_service = FlairService()  # No carga el modelo al inicializar
        logger.info("Servicio Flair inicializado (carga diferida)")
    except Exception as e:
        logger.warning(f"No se pudo inicializar servicio Flair: {str(e)}")

    # Inicializar servicios
    entity_service = CorePresidioService(flair_service=flair_service)
    file_processor = FileProcessor()
    orchestrator_service = PresidioOrchestratorService(
        entity_service, file_processor, logger
    )
    controller = PresidioController(orchestrator_service, logger)
    controller.register_routes(app)

    return app


if __name__ == "__main__":
    app = create_app()
    # En Docker configuramos para que los logs vayan a stdout
    import os

    is_docker = os.environ.get("RUNNING_IN_DOCKER", False)
    debug_mode = (
        not is_docker
    )  # Desactivar debug mode en Docker para no interferir con los logs
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
