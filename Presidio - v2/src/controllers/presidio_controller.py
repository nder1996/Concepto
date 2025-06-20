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
        self.logger.info("Iniciando análisis de texto")
        try:
            data = request.json
            text = data['text']
            # Extraer el idioma del JSON, por defecto 'es' si no se proporciona
            language = data.get('language', 'es')
            self.logger.info(f"Analizando texto de {len(text)} caracteres en idioma: {language}")
            
            results = self.presidio_service.analyze_text(text, language=language)
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
            # Extraer el idioma del JSON, por defecto 'es' si no se proporciona
            language = data.get('language', 'es')
            self.logger.info(f"Anonimizando texto de {len(text)} caracteres en idioma: {language}")
            
            anonymized_text = self.presidio_service.anonymize_text(text, language=language)
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
            
            # Extraer el idioma de los parámetros, por defecto 'es' si no se proporciona
            language = request.form.get('language', 'es')
            self.logger.info(f"Analizando archivo en idioma: {language}")
            
            # Analizar texto extraído
            results = self.presidio_service.analyze_text(extracted_text, language=language)
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
            
            # Extraer el idioma de los parámetros, por defecto 'es' si no se proporciona
            language = request.form.get('language', 'es')
            self.logger.info(f"Anonimizando archivo en idioma: {language}")
            
            # Anonimizar texto extraído
            anonymized_text = self.presidio_service.anonymize_text(extracted_text, language=language)
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
        """Endpoint para verificar salud del servicio"""
        self.logger.info("Verificando salud del servicio")
        
        try:
            # Obtener idiomas soportados desde el servicio
            supported_languages = self.presidio_service.supported_languages
            default_language = self.presidio_service.default_language
            
            response = {
                'status': 'healthy',
                'supported_languages': supported_languages,
                'default_language': default_language,
                'version': '1.0.0'
            }
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error en health check: {str(e)}")
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    def preview_anonymization_text(self):
        """
        Endpoint para previsualizar qué palabras serán anonimizadas en texto sin realizar la anonimización.
        Acepta únicamente texto y devuelve las entidades detectadas con su contexto.
        """
        self.logger.info("Iniciando previsualización de anonimización de texto")
        try:
            text = None
            language = 'es'  # Valor predeterminado en español
            
            # Verificar si es una solicitud JSON
            content_type = request.headers.get('Content-Type', '')
            self.logger.info(f"Content-Type recibido: {content_type}")
            
            # Para solicitudes application/json
            if request.is_json:
                self.logger.info("Procesando petición JSON")
                try:
                    data = request.get_json(force=True)                  
                    if 'text' in data:
                        text = data['text']
                        language = data.get('language', 'es')
                    else:
                        return jsonify({'error': 'Se requiere el campo "text" en el JSON para previsualización'}), 400
                except Exception as e:
                    return jsonify({'error': f'Error al procesar JSON: {str(e)}'}), 400
            
            # Para solicitudes form-urlencoded
            elif request.form and 'text' in request.form:
                self.logger.info("Procesando texto desde formulario")
                text = request.form.get('text')
                language = request.form.get('language', 'es')
            
            # Si no se reconoce el formato, pero hay datos
            else:
                # Intentar procesar como JSON sin importar el Content-Type
                try:
                    data = request.get_json(force=True, silent=True)    
                    if data and 'text' in data:
                        self.logger.info("Forzando procesamiento como JSON")
                        text = data['text']
                        language = data.get('language', 'es')
                    else:
                        return jsonify({
                            'error': 'No se encontró texto para previsualización',
                            'content_type': content_type,
                            'tip': 'Envíe un objeto JSON con el campo "text" o use form-urlencoded'
                        }), 400
                except Exception:
                    return jsonify({
                        'error': 'No se pudo interpretar la solicitud. Content-Type incorrecto o datos malformados',
                        'content_type_recibido': content_type,
                        'tip': 'Use application/json con un campo "text" o form-urlencoded'
                    }), 400
            
            if not text:
                return jsonify({'error': 'No se proporcionó texto para analizar'}), 400
                
            self.logger.info(f"Analizando texto para previsualización (idioma: {language})")
            
            # Analizar el texto para detectar entidades
            analysis_results = self.presidio_service.analyze_text(text, language=language)
            
            # Enriquecer los resultados con el texto original de cada entidad
            for result in analysis_results:
                result['texto_original'] = text[result['start']:result['end']]
            
            self.logger.info(f"Previsualización de texto completada: {len(analysis_results)} entidades encontradas")
            
            # Preparar la respuesta
            response = {
                'fuente': 'text',
                'texto_completo': text,
                'entidades_detectadas': analysis_results,
                'total_entidades': len(analysis_results)
            }
                
            return jsonify(response)
            
        except Exception as e:
            self.logger.error(f"Error en previsualización de texto: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    def preview_anonymization_file(self):
        """
        Endpoint para previsualizar qué palabras serán anonimizadas en archivos sin realizar la anonimización.
        Acepta únicamente archivos y devuelve las entidades detectadas con su contexto.
        """
        self.logger.info("Iniciando previsualización de anonimización de archivo")
        try:
            # Verificar si se envió un archivo
            if 'file' not in request.files:
                return jsonify({'error': 'No se proporcionó archivo'}), 400
                
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
            
            file_content = file.read()
            language = request.form.get('language', 'es')
            
            # Procesar el archivo según su tipo
            self.logger.info(f"Procesando archivo para previsualización: {file.filename}")
            try:
                text = self.file_processor.process_file(file_content, file.filename)
                if not text:
                    return jsonify({'error': 'No se pudo extraer texto del archivo'}), 400
            except Exception as e:
                return jsonify({'error': f'Error al procesar el archivo: {str(e)}'}), 400
            
            self.logger.info(f"Analizando archivo para previsualización (idioma: {language})")
            
            # Analizar el texto para detectar entidades
            analysis_results = self.presidio_service.analyze_text(text, language=language)
            
            # Enriquecer los resultados con el texto original de cada entidad
            for result in analysis_results:
                result['texto_original'] = text[result['start']:result['end']]
            
            self.logger.info(f"Previsualización de archivo completada: {len(analysis_results)} entidades encontradas")
            
            # Preparar la respuesta
            response = {
                'fuente': 'file',
                'nombre_archivo': file.filename,
                'texto_completo': text,
                'entidades_detectadas': analysis_results,
                'total_entidades': len(analysis_results)
            }
                
            return jsonify(response)
            
        except Exception as e:
            self.logger.error(f"Error en previsualización de archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500