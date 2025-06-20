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
        app.add_url_rule('/preview-anonymization-text', 'preview_anonymization_text', self.preview_anonymization_text, methods=['POST'])
        app.add_url_rule('/preview-anonymization-file', 'preview_anonymization_file', self.preview_anonymization_file, methods=['POST'])
        app.add_url_rule('/health', 'health', self.health, methods=['GET'])

    def analyze(self):
        """Endpoint para analizar texto"""
        try:
            data = request.json
            text = data['text']
            language = data.get('language', 'es')
            
            results = self.presidio_service.analyze_text(text, language=language)
            return jsonify(results)
        except Exception as e:
            return self._error_response(e)
    
    def anonymize(self):
        """Endpoint para anonimizar texto"""
        try:
            data = request.json
            text = data['text']
            language = data.get('language', 'es')
            
            anonymized_text = self.presidio_service.anonymize_text(text, language=language)
            return jsonify({'text': anonymized_text})
        except Exception as e:
            return self._error_response(e)
    
    def analyze_file(self):
        """Endpoint para analizar archivos"""
        try:
            file = self._get_file_from_request()
            text = self._extract_text_from_file(file)
            language = request.form.get('language', 'es')
            
            results = self.presidio_service.analyze_text(text, language=language)
            
            return jsonify({
                'filename': file.filename,
                'extracted_text': text,
                'entities': results
            })
        except Exception as e:
            return self._error_response(e)
    
    def anonymize_file(self):
        """Endpoint para anonimizar archivos"""
        try:
            file = self._get_file_from_request()
            text = self._extract_text_from_file(file)
            language = request.form.get('language', 'es')
            
            anonymized_text = self.presidio_service.anonymize_text(text, language=language)
            
            return jsonify({
                'filename': file.filename,
                'original_text': text,
                'anonymized_text': anonymized_text
            })
        except Exception as e:
            return self._error_response(e)
    
    def preview_anonymization_text(self):
        """Previsualizar anonimización de texto"""
        try:
            # Obtener texto de JSON o form
            data = request.get_json(force=True, silent=True) or {}
            text = data.get('text') or request.form.get('text')
            language = data.get('language') or request.form.get('language', 'es')
            
            if not text:
                return jsonify({'error': 'Se requiere el campo "text"'}), 400
            
            results = self._get_preview_results(text, language)
            
            return jsonify({
                'fuente': 'text',
                'texto_completo': text,
                'entidades_detectadas': results,
                'total_entidades': len(results)
            })
        except Exception as e:
            return self._error_response(e)
    
    def preview_anonymization_file(self):
        """Previsualizar anonimización de archivo"""
        try:
            file = self._get_file_from_request()
            text = self._extract_text_from_file(file)
            language = request.form.get('language', 'es')
            
            results = self._get_preview_results(text, language)
            
            return jsonify({
                'fuente': 'file',
                'nombre_archivo': file.filename,
                'texto_completo': text,
                'entidades_detectadas': results,
                'total_entidades': len(results)
            })
        except Exception as e:
            return self._error_response(e)
    
    def health(self):
        """Endpoint para verificar salud del servicio"""
        try:
            return jsonify({
                'status': 'healthy',
                'supported_languages': self.presidio_service.supported_languages,
                'default_language': self.presidio_service.default_language,
                'version': '1.0.0'
            })
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    # Métodos helper privados
    def _get_file_from_request(self):
        """Obtiene y valida archivo de la request"""
        if 'file' not in request.files:
            raise ValueError('No se proporcionó archivo')
        
        file = request.files['file']
        if file.filename == '':
            raise ValueError('No se seleccionó ningún archivo')
        
        return file
    
    def _extract_text_from_file(self, file):
        """Extrae texto del archivo"""
        file_content = file.read()
        text = self.file_processor.process_file(file_content, file.filename)
        
        if not text:
            raise ValueError('No se pudo extraer texto del archivo')
        
        return text
    
    def _get_preview_results(self, text, language):
        """Obtiene resultados de previsualización con texto original"""
        results = self.presidio_service.analyze_text(text, language=language)
        
        # Agregar texto original a cada resultado
        for result in results:
            result['texto_original'] = text[result['start']:result['end']]
        
        return results
    
    def _error_response(self, error):
        """Maneja respuestas de error de forma consistente"""
        self.logger.error(f"Error en endpoint: {str(error)}")
        return jsonify({'error': str(error)}), 500