from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import BadRequest, InternalServerError
import traceback
import io
from typing import Dict, Any, List
import json

class ApiController:
    """
    Controlador principal de la API Flask para el servicio de anonimización.
    Maneja todas las rutas HTTP y coordina con los servicios de negocio.
    """
    
    def __init__(self, anonymization_service, logger):
        self.anonymization_service = anonymization_service
        self.logger = logger
        
    def register_routes(self, app: Flask):
        """Registra todas las rutas de la API"""
        
        @app.route('/', methods=['GET'])
        def health_check():
            """Endpoint de verificación de salud del servicio"""
            try:
                return jsonify({
                    "status": "healthy",
                    "service": "Presidio Anonymization API",
                    "version": "1.0.0",
                    "supported_languages": ["es", "en"],
                    "endpoints": {
                        "analyze": "/analyze - POST - Analiza texto para detectar PII",
                        "anonymize": "/anonymize - POST - Anonimiza texto",
                        "analyze_file": "/analyze-file - POST - Analiza archivo",
                        "anonymize_file": "/anonymize-file - POST - Anonimiza archivo",
                        "preview": "/preview - POST - Previsualiza anonimización"
                    }
                }), 200
            except Exception as e:
                self.logger.error(f"Error en health check: {str(e)}")
                return jsonify({"error": "Service unavailable"}), 503

        @app.route('/analyze', methods=['POST'])
        def analyze_text():
            """Analiza texto para detectar información personal (PII)"""
            try:
                # Validar que se recibió JSON
                if not request.is_json:
                    raise BadRequest("Content-Type debe ser application/json")
                
                data = request.get_json()
                
                # Validar parámetros requeridos
                if 'text' not in data:
                    raise BadRequest("Parámetro 'text' es requerido")
                
                text = data['text']
                if not text or not text.strip():
                    raise BadRequest("El texto no puede estar vacío")
                
                # Parámetros opcionales
                language = data.get('language', 'es')
                
                self.logger.info(f"Analizando texto de {len(text)} caracteres en idioma {language}")
                
                # Realizar análisis
                entities = self.anonymization_service.analyze_text(text, language)
                
                # Preparar respuesta
                response = {
                    "status": "success",
                    "language": language,
                    "language_name": self.anonymization_service.get_language_name(language),
                    "text_length": len(text),
                    "entities_found": len(entities),
                    "entities": entities
                }
                
                return jsonify(response), 200
                
            except BadRequest as e:
                self.logger.warning(f"Bad request en analyze: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                self.logger.error(f"Error en analyze: {str(e)}")
                self.logger.error(traceback.format_exc())
                return jsonify({"error": "Error interno del servidor"}), 500

        @app.route('/anonymize', methods=['POST'])
        def anonymize_text():
            """Anonimiza texto reemplazando información personal detectada"""
            try:
                # Validar que se recibió JSON
                if not request.is_json:
                    raise BadRequest("Content-Type debe ser application/json")
                
                data = request.get_json()
                
                # Validar parámetros requeridos
                if 'text' not in data:
                    raise BadRequest("Parámetro 'text' es requerido")
                
                text = data['text']
                if not text or not text.strip():
                    raise BadRequest("El texto no puede estar vacío")
                
                # Parámetros opcionales
                language = data.get('language', 'es')
                
                self.logger.info(f"Anonimizando texto de {len(text)} caracteres en idioma {language}")
                
                # Realizar anonimización
                anonymized_text = self.anonymization_service.anonymize_text(text, language)
                
                # Preparar respuesta
                response = {
                    "status": "success",
                    "language": language,
                    "language_name": self.anonymization_service.get_language_name(language),
                    "original_length": len(text),
                    "anonymized_length": len(anonymized_text),
                    "original_text": text,
                    "anonymized_text": anonymized_text
                }
                
                return jsonify(response), 200
                
            except BadRequest as e:
                self.logger.warning(f"Bad request en anonymize: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                self.logger.error(f"Error en anonymize: {str(e)}")
                self.logger.error(traceback.format_exc())
                return jsonify({"error": "Error interno del servidor"}), 500

        @app.route('/analyze-file', methods=['POST'])
        def analyze_file():
            """Analiza un archivo para detectar información personal"""
            try:
                # Validar que se recibió un archivo
                if 'file' not in request.files:
                    raise BadRequest("No se recibió ningún archivo")
                
                file = request.files['file']
                if file.filename == '':
                    raise BadRequest("No se seleccionó ningún archivo")
                
                # Parámetros opcionales
                language = request.form.get('language', 'es')
                
                self.logger.info(f"Analizando archivo: {file.filename} en idioma {language}")
                
                # Leer contenido del archivo
                file_content = file.read()
                
                # Analizar archivo
                result = self.anonymization_service.analyze_file(
                    file_content, 
                    file.filename, 
                    language
                )
                
                # Preparar respuesta
                response = {
                    "status": "success",
                    "filename": result['filename'],
                    "language": result['language'],
                    "language_name": result['language_name'],
                    "extracted_text_length": len(result['extracted_text']),
                    "entities_found": result['total_entities'],
                    "entities": result['entities'],
                    "extracted_text": result['extracted_text']
                }
                
                return jsonify(response), 200
                
            except BadRequest as e:
                self.logger.warning(f"Bad request en analyze-file: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                self.logger.error(f"Error en analyze-file: {str(e)}")
                self.logger.error(traceback.format_exc())
                return jsonify({"error": "Error interno del servidor"}), 500

        @app.route('/anonymize-file', methods=['POST'])
        def anonymize_file():
            """Anonimiza un archivo"""
            try:
                # Validar que se recibió un archivo
                if 'file' not in request.files:
                    raise BadRequest("No se recibió ningún archivo")
                
                file = request.files['file']
                if file.filename == '':
                    raise BadRequest("No se seleccionó ningún archivo")
                
                # Parámetros opcionales
                language = request.form.get('language', 'es')
                
                self.logger.info(f"Anonimizando archivo: {file.filename} en idioma {language}")
                
                # Leer contenido del archivo
                file_content = file.read()
                
                # Anonimizar archivo
                result = self.anonymization_service.anonymize_file(
                    file_content, 
                    file.filename, 
                    language
                )
                
                # Preparar respuesta
                response = {
                    "status": "success",
                    "filename": result['filename'],
                    "language": result['language'],
                    "language_name": result['language_name'],
                    "original_text": result['original_text'],
                    "anonymized_text": result['anonymized_text'],
                    "original_length": len(result['original_text']),
                    "anonymized_length": len(result['anonymized_text'])
                }
                
                return jsonify(response), 200
                
            except BadRequest as e:
                self.logger.warning(f"Bad request en anonymize-file: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                self.logger.error(f"Error en anonymize-file: {str(e)}")
                self.logger.error(traceback.format_exc())
                return jsonify({"error": "Error interno del servidor"}), 500

        @app.route('/preview', methods=['POST'])
        def preview_anonymization():
            """Previsualiza la anonimización sin aplicarla"""
            try:
                # Validar que se recibió JSON
                if not request.is_json:
                    raise BadRequest("Content-Type debe ser application/json")
                
                data = request.get_json()
                
                # Validar parámetros requeridos
                if 'text' not in data:
                    raise BadRequest("Parámetro 'text' es requerido")
                
                text = data['text']
                if not text or not text.strip():
                    raise BadRequest("El texto no puede estar vacío")
                
                # Parámetros opcionales
                language = data.get('language', 'es')
                
                self.logger.info(f"Previsualizando anonimización de texto de {len(text)} caracteres")
                
                # Realizar previsualización
                preview_result = self.anonymization_service.preview_anonymization(text, language)
                
                return jsonify(preview_result), 200
                
            except BadRequest as e:
                self.logger.warning(f"Bad request en preview: {str(e)}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                self.logger.error(f"Error en preview: {str(e)}")
                self.logger.error(traceback.format_exc())
                return jsonify({"error": "Error interno del servidor"}), 500

        @app.errorhandler(404)
        def not_found(error):
            """Maneja errores 404"""
            return jsonify({
                "error": "Endpoint no encontrado",
                "available_endpoints": {
                    "/": "GET - Health check",
                    "/analyze": "POST - Analiza texto",
                    "/anonymize": "POST - Anonimiza texto",
                    "/analyze-file": "POST - Analiza archivo",
                    "/anonymize-file": "POST - Anonimiza archivo",
                    "/preview": "POST - Previsualiza anonimización"
                }
            }), 404

        @app.errorhandler(500)
        def internal_error(error):
            """Maneja errores 500"""
            self.logger.error(f"Error interno del servidor: {str(error)}")
            return jsonify({"error": "Error interno del servidor"}), 500