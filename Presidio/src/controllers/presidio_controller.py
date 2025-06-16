from flask import request, jsonify
from src.services.presidio_orchestrator_service import PresidioOrchestratorService
import logging

class PresidioController:
    def __init__(self, orchestrator_service: PresidioOrchestratorService, logger: logging.Logger):
        """
        Inicializa el controlador de Presidio con un servicio orquestador
        
        Args:
            orchestrator_service: Servicio orquestador que maneja la lógica de negocio
            logger: Logger centralizado para registro de eventos
        """
        self.orchestrator = orchestrator_service
        self.logger = logger
        
    def register_routes(self, app):
        """
        Registra todas las rutas en la aplicación Flask
        
        Args:
            app: Instancia de la aplicación Flask
        """
        app.add_url_rule('/analyze', 'analyze', self.analyze, methods=['POST'])
        app.add_url_rule('/anonymize', 'anonymize', self.anonymize, methods=['POST'])
        app.add_url_rule('/analyze-file', 'analyze_file', self.analyze_file, methods=['POST'])
        app.add_url_rule('/anonymize-file', 'anonymize_file', self.anonymize_file, methods=['POST'])
        app.add_url_rule('/preview-anonymization-text', 'preview_anonymization_text', self.preview_anonymization_text, methods=['POST'])
        app.add_url_rule('/preview-anonymization-file', 'preview_anonymization_file', self.preview_anonymization_file, methods=['POST'])
        app.add_url_rule('/health', 'health', self.health, methods=['GET'])
        app.add_url_rule('/recognizers', 'get_recognizer_entities', self.get_recognizer_entities, methods=['GET'])
        app.add_url_rule('/recognizer-examples', 'generate_recognizer_examples', self.generate_recognizer_examples, methods=['GET'])
    
    def _get_language_from_request(self):
        """
        Extrae el idioma de la solicitud HTTP
        
        Returns:
            Código de idioma extraído de la solicitud
        """
        # Extraer el idioma de la solicitud JSON
        if request.json and 'language' in request.json:
            return request.json.get('language')
        
        # O del formulario o query string        return request.form.get('language', request.args.get('language'))
        
    def analyze(self):
        """
        Endpoint para analizar texto
        
        Returns:
            Respuesta JSON con los resultados del análisis
        """
        import json
        endpoint_info = {
            "method": "POST",
            "endpoint": "/analyze",
            "type": "text",
            "timestamp": __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.logger.info(f"[API] {json.dumps(endpoint_info)}")
        
        try:
            data = request.json
            text = data['text']
            language = self._get_language_from_request()
            
            # Delegar al orquestador la lógica de análisis
            response = self.orchestrator.analyze_text(text, language)
            return jsonify(response)
        except Exception as e:
            error_info = {
                "status": "error",
                "endpoint": "/analyze",
                "error": str(e)
            }
            self.logger.error(f"[Error] {json.dumps(error_info)}")
            return jsonify({'error': str(e)}), 500
    
    def anonymize(self):
        """
        Endpoint para anonimizar texto
        
        Returns:
            Respuesta JSON con texto anonimizado y metadatos
        """
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /anonymize (Texto)")
        self.logger.info("=" * 50)
        
        try:
            data = request.json
            text = data['text']
            language = self._get_language_from_request()
            
            # Delegar al orquestador la lógica de anonimización
            response = self.orchestrator.anonymize_text(text, language)
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error en anonimización: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def analyze_file(self):
        """
        Endpoint para analizar archivos
        
        Returns:
            Respuesta JSON con los resultados del análisis del contenido del archivo
        """
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /analyze-file")
        self.logger.info("=" * 50)
        
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No se ha proporcionado ningún archivo'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No se ha seleccionado ningún archivo'}), 400
            
            language = self._get_language_from_request()
            
            # Procesar el archivo y extraer texto
            file_content = file.read()
            text = self.orchestrator.process_file(file_content, file.filename)
            
            # Analizar el texto extraído
            response = self.orchestrator.analyze_text(text, language)
            
            # Añadir información adicional del archivo
            response['filename'] = file.filename
            response['text'] = text
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error en análisis de archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def anonymize_file(self):
        """
        Endpoint para anonimizar archivos
        
        Returns:
            Respuesta JSON con texto anonimizado y metadatos
        """
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /anonymize-file")
        self.logger.info("=" * 50)
        
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No se ha proporcionado ningún archivo'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No se ha seleccionado ningún archivo'}), 400
            
            language = self._get_language_from_request()
            
            # Procesar el archivo y extraer texto
            file_content = file.read()
            text = self.orchestrator.process_file(file_content, file.filename)
            
            # Anonimizar el texto extraído
            response = self.orchestrator.anonymize_text(text, language)
            
            # Añadir información adicional del archivo
            response['filename'] = file.filename
            response['original_text'] = text
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error en anonimización de archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    def preview_anonymization_text(self):
        """
        Endpoint para previsualizar anonimización de texto
        
        Returns:
            Respuesta JSON con resultados de análisis y anonimización
        """
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /preview-anonymization-text")
        self.logger.info("=" * 50)
        
        try:
            data = request.json
            text = data['text']
            language = self._get_language_from_request()
            
            # Delegar al orquestador la previsualización
            response = self.orchestrator.preview_anonymization(text, language)
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error en previsualización: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    def preview_anonymization_file(self):
        """
        Endpoint para previsualizar anonimización de archivos
        
        Returns:
            Respuesta JSON con resultados de análisis y anonimización
        """
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /preview-anonymization-file")
        self.logger.info("=" * 50)
        
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No se ha proporcionado ningún archivo'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No se ha seleccionado ningún archivo'}), 400
            
            language = self._get_language_from_request()
            
            # Procesar el archivo y extraer texto
            file_content = file.read()
            text = self.orchestrator.process_file(file_content, file.filename)
            
            # Realizar previsualización
            response = self.orchestrator.preview_anonymization(text, language)
            
            # Añadir información adicional del archivo
            response['original_text'] = text
            response['filename'] = file.filename
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error en previsualización de archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    def health(self):
        """
        Endpoint para verificar la salud del servicio
        
        Returns:
            Respuesta JSON con estado del servicio
        """
        self.logger.info("Verificación de salud solicitada")
        
        # Verificar el estado de los servicios
        response = self.orchestrator.get_service_status()
        return jsonify(response)
        
    def get_recognizer_entities(self):
        """
        Devuelve información sobre los tipos de entidades reconocibles
        
        Returns:
            Respuesta JSON con información sobre reconocedores
        """
        self.logger.info("Solicitando información de reconocedores personalizados")
        
        response = self.orchestrator.get_recognizers_info()
        return jsonify(response)
    
    def generate_recognizer_examples(self):
        """
        Genera ejemplos para los tipos de entidades reconocibles
        
        Returns:
            Respuesta JSON con ejemplos para cada tipo de entidad
        """
        self.logger.info("Solicitando ejemplos de reconocedores personalizados")
        
        response = self.orchestrator.generate_recognizer_examples()
        return jsonify(response)
