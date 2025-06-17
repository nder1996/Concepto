from flask import request, jsonify
from src.services.presidio_service import PresidioService
from src.services.file_processor import FileProcessor
import logging

class PresidioController:
    def __init__(self, presidio_service: PresidioService, file_processor: FileProcessor, logger: logging.Logger):
        self.presidio_service = presidio_service
        self.file_processor = file_processor
        self.logger = logger
    
    def register_routes(self, app):
        """Registra todas las rutas en la aplicación Flask"""
        app.add_url_rule('/analyze', 'analyze', self.analyze, methods=['POST'])
        app.add_url_rule('/anonymize', 'anonymize', self.anonymize, methods=['POST'])
        app.add_url_rule('/analyze-file', 'analyze_file', self.analyze_file, methods=['POST'])
        app.add_url_rule('/anonymize-file', 'anonymize_file', self.anonymize_file, methods=['POST'])
        app.add_url_rule('/preview-anonymization', 'preview_anonymization', self.preview_anonymization, methods=['POST'])
        app.add_url_rule('/health', 'health', self.health, methods=['GET'])
    
    def analyze(self):
        """Endpoint para analizar texto"""
        self.logger.info("Iniciando análisis de texto")
        try:
            data = request.json
            text = data['text']
            self.logger.info(f"Analizando texto de {len(text)} caracteres")
            
            results = self.presidio_service.analyze_text(text)
            self.logger.info(f"Análisis completado: {len(results)} entidades encontradas")
            
            return jsonify(results)
        except Exception as e:
            self.logger.error(f"Error en análisis: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def anonymize(self):
        """Endpoint para anonimizar texto"""
        self.logger.info("Iniciando anonimización de texto")
        try:
            data = request.json
            text = data['text']
            self.logger.info(f"Anonimizando texto de {len(text)} caracteres")
            
            anonymized_text = self.presidio_service.anonymize_text(text)
            self.logger.info("Anonimización completada exitosamente")
            
            return jsonify({'text': anonymized_text})
        except Exception as e:
            self.logger.error(f"Error en anonimización: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def analyze_file(self):
        """Endpoint para analizar archivos"""
        self.logger.info("Iniciando análisis de archivo")
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No se proporcionó archivo'}), 400
            
            file = request.files['file']
            file_content = file.read()
            
            self.logger.info(f"Procesando archivo: {file.filename}")
            
            # Extraer texto del archivo
            extracted_text = self.file_processor.process_file(file_content, file.filename)
            self.logger.info(f"Texto extraído: {len(extracted_text)} caracteres")
            
            # Analizar texto extraído
            results = self.presidio_service.analyze_text(extracted_text)
            self.logger.info(f"Archivo analizado: {len(results)} entidades encontradas")
            
            response = {
                'filename': file.filename,
                'extracted_text': extracted_text,
                'entities': results
            }
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error procesando archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def anonymize_file(self):
        """Endpoint para anonimizar archivos"""
        self.logger.info("Iniciando anonimización de archivo")
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No se proporcionó archivo'}), 400
            
            file = request.files['file']
            file_content = file.read()
            
            self.logger.info(f"Anonimizando archivo: {file.filename}")
            
            # Extraer texto del archivo
            extracted_text = self.file_processor.process_file(file_content, file.filename)
            
            # Anonimizar texto extraído
            anonymized_text = self.presidio_service.anonymize_text(extracted_text)
            self.logger.info("Archivo anonimizado exitosamente")
            
            response = {
                'filename': file.filename,
                'original_text': extracted_text,
                'anonymized_text': anonymized_text
            }
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error anonimizando archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def health(self):
        """Endpoint de salud"""
        self.logger.info("Health check solicitado")
        return jsonify({'status': 'healthy', 'service': 'Presidio API'})
          def preview_anonymization(self):
        """
        Endpoint para previsualizar qué palabras serán anonimizadas sin realizar la anonimización.
        Acepta texto directo o un archivo y devuelve las entidades detectadas con su contexto.
        """
        self.logger.info("Iniciando previsualización de anonimización")
        try:
            text = None
            source_type = None
            filename = None
            content_type = request.headers.get('Content-Type', '')
            self.logger.info(f"Content-Type recibido: {content_type}")
            
            # Verificar el Content-Type y manejar los datos adecuadamente
            if 'multipart/form-data' in content_type:
                # Verificar si se envió un archivo
                if 'file' in request.files:
                    file = request.files['file']
                    if file.filename == '':
                        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
                    
                    source_type = 'file'
                    filename = file.filename
                    file_content = file.read()
                    
                    # Procesar el archivo según su tipo
                    self.logger.info(f"Procesando archivo para previsualización: {filename}")
                    text = self.file_processor.process_file(file_content, filename)
                    if not text:
                        return jsonify({'error': 'No se pudo extraer texto del archivo'}), 400
                # Verificar si se envió texto desde un formulario
                elif request.form.get('text'):
                    source_type = 'text'
                    text = request.form.get('text')
                else:
                    return jsonify({'error': 'Se requiere un archivo o texto para la previsualización'}), 400
                
                # Obtener configuración opcional desde el formulario
                language = request.form.get('language') or 'en'
                
            elif 'application/json' in content_type:
                # Verificar que existan datos JSON
                if not request.is_json:
                    return jsonify({'error': 'Se esperaba contenido JSON pero no se proporcionó'}), 415
                
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No se proporcionaron datos JSON'}), 400
                
                # Verificar si se envió texto en JSON
                if 'text' in data:
                    source_type = 'text'
                    text = data['text']
                    # Obtener configuración opcional desde JSON
                    language = data.get('language', 'en')
                else:
                    return jsonify({'error': 'Se requiere el campo "text" en el JSON para la previsualización'}), 400
            else:
                return jsonify({
                    'error': 'Content-Type no soportado. Utilice application/json para texto o multipart/form-data para archivos',
                    'content_type_recibido': content_type
                }), 415
            
            self.logger.info(f"Analizando texto para previsualización (idioma: {language})")
            
            # Analizar el texto para detectar entidades
            analysis_results = self.presidio_service.analyze_text(text, language=language)
            
            # Enriquecer los resultados con el texto original de cada entidad
            for result in analysis_results:
                result['texto_original'] = text[result['start']:result['end']]
            
            self.logger.info(f"Previsualización completada: {len(analysis_results)} entidades encontradas")
            
            # Preparar la respuesta
            response = {
                'fuente': source_type,
                'texto_completo': text,
                'entidades_detectadas': analysis_results,
                'total_entidades': len(analysis_results)
            }
            
            if filename:
                response['nombre_archivo'] = filename
                
            return jsonify(response)
            
        except Exception as e:
            self.logger.error(f"Error en previsualización: {str(e)}")
            return jsonify({'error': str(e)}), 500