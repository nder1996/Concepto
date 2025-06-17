from flask import request, jsonify
from src.services.presidio_service import PresidioService
from src.services.file_processor import FileProcessor
import logging

class PresidioController: 
    def __init__(self, presidio_service: PresidioService, file_processor: FileProcessor, logger: logging.Logger):
        self.presidio_service = presidio_service
        self.file_processor = file_processor
        self.logger = logger
        # Cambiamos el idioma predeterminado a español para mayor coherencia con el texto enviado
        self.default_language = 'es'
        self.supported_languages = ['en', 'es']
        
        # Mapeo de códigos de idioma a nombres descriptivos
        self.language_names = {
            'en': 'inglés',
            'es': 'español'
        }
    
    def register_routes(self, app):
        """Registra todas las rutas en la aplicación Flask"""
        app.add_url_rule('/analyze', 'analyze', self.analyze, methods=['POST'])
        app.add_url_rule('/anonymize', 'anonymize', self.anonymize, methods=['POST'])
        app.add_url_rule('/analyze-file', 'analyze_file', self.analyze_file, methods=['POST'])
        app.add_url_rule('/anonymize-file', 'anonymize_file', self.anonymize_file, methods=['POST'])
        app.add_url_rule('/preview-anonymization-text', 'preview_anonymization_text', self.preview_anonymization_text, methods=['POST'])
        app.add_url_rule('/preview-anonymization-file', 'preview_anonymization_file', self.preview_anonymization_file, methods=['POST'])
        app.add_url_rule('/health', 'health', self.health, methods=['GET'])
    
    def _get_language_name(self, language_code):
        """Devuelve el nombre descriptivo del idioma en base al código"""
        return self.language_names.get(language_code, f"desconocido ({language_code})")
        
    def _get_language_from_request(self, data=None):
        """Extrae y valida el idioma de la solicitud"""
        # Si se proporciona data directamente (de request.json)
        if data and isinstance(data, dict) and 'language' in data:
            language = data.get('language', self.default_language).lower()
        # Si no, intentar obtenerlo del formulario o query string
        else:
            language = request.form.get('language', 
                       request.args.get('language', self.default_language)).lower()
        
        # Validar que el idioma sea soportado
        if language not in self.supported_languages:
            self.logger.warning(f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}")
            language = self.default_language
            
        return language 
    def analyze(self):
        """Endpoint para analizar texto"""
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /analyze (Texto)")
        self.logger.info("=" * 50)
        
        try:
            data = request.json
            text = data['text']
            language = self._get_language_from_request(data)
            language_name = self._get_language_name(language)
            
            self.logger.info(f"Request recibido:")
            self.logger.info(f"- Idioma: {language} ({language_name})")
            self.logger.info(f"- Longitud del texto: {len(text)} caracteres")
            self.logger.info(f"- Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            results = self.presidio_service.analyze_text(text, language=language)
            
            # Añadir el texto específico de cada entidad a los resultados
            for entity in results:
                entity['text'] = text[entity['start']:entity['end']]
            
            self.logger.info("Resultado del análisis:")
            self.logger.info(f"- Total entidades encontradas: {len(results)}")
            for idx, entity in enumerate(results[:5]):  # Limitar a 5 para no saturar los logs
                self.logger.info(f"  Entidad {idx+1}: {entity['entity_type']} - '{entity['text']}' (score: {entity['score']:.2f})")
            if len(results) > 5:
                self.logger.info(f"  ... y {len(results)-5} entidades más")
            
            return jsonify({
                'results': results,
                'language': language,
                'language_name': language_name,
                'total_entities': len(results)
            })
        except Exception as e:
            self.logger.error(f"Error en análisis: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def anonymize(self):
        """Endpoint para anonimizar texto"""
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /anonymize (Texto)")
        self.logger.info("=" * 50)
        
        try:
            data = request.json
            text = data['text']
            language = self._get_language_from_request(data)
            language_name = self._get_language_name(language)
            
            self.logger.info(f"Request recibido:")
            self.logger.info(f"- Idioma: {language} ({language_name})")
            self.logger.info(f"- Longitud del texto: {len(text)} caracteres")
            self.logger.info(f"- Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            anonymized_text = self.presidio_service.anonymize_text(text, language=language)
            
            self.logger.info("Resultado de la anonimización:")
            self.logger.info(f"- Longitud del texto anonimizado: {len(anonymized_text)} caracteres")
            self.logger.info(f"- Contenido anonimizado: '{anonymized_text[:100]}{'...' if len(anonymized_text) > 100 else ''}'")
            
            return jsonify({
                'text': anonymized_text,
                'language': language,
                'language_name': language_name
            })
        except Exception as e:
            self.logger.error(f"Error en anonimización: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def analyze_file(self):
        """Endpoint para analizar archivos"""
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /analyze-file (Archivo)")
        self.logger.info("=" * 50)
        
        try:
            if 'file' not in request.files:
                self.logger.error("No se proporcionó archivo en la solicitud")
                return jsonify({'error': 'No se proporcionó archivo'}), 400
            
            file = request.files['file']
            file_content = file.read()
            language = self._get_language_from_request()
            language_name = self._get_language_name(language)
            
            self.logger.info(f"Request recibido:")
            self.logger.info(f"- Archivo: {file.filename}")
            self.logger.info(f"- Idioma: {language} ({language_name})")
            
            # Extraer texto del archivo
            extracted_text = self.file_processor.process_file(file_content, file.filename)
            self.logger.info(f"Texto extraído: {len(extracted_text)} caracteres")
            self.logger.info(f"- Contenido: '{extracted_text[:100]}{'...' if len(extracted_text) > 100 else ''}'")
            
            # Analizar texto extraído
            results = self.presidio_service.analyze_text(extracted_text, language=language)
            
            self.logger.info("Resultado del análisis:")
            self.logger.info(f"- Total entidades encontradas: {len(results)}")
            for idx, entity in enumerate(results[:5]):  # Limitar a 5 para no saturar los logs
                self.logger.info(f"  Entidad {idx+1}: {entity['entity_type']} - '{extracted_text[entity['start']:entity['end']]}' (score: {entity['score']:.2f})")
            if len(results) > 5:
                self.logger.info(f"  ... y {len(results)-5} entidades más")
            
            response = {
                'filename': file.filename,
                'extracted_text': extracted_text,
                'entities': results,
                'language': language,
                'language_name': language_name,
                'total_entities': len(results)
            }
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error procesando archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def anonymize_file(self):
        """Endpoint para anonimizar archivos"""
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /anonymize-file (Archivo)")
        self.logger.info("=" * 50)
        
        try:
            if 'file' not in request.files:
                self.logger.error("No se proporcionó archivo en la solicitud")
                return jsonify({'error': 'No se proporcionó archivo'}), 400
            
            file = request.files['file']
            file_content = file.read()
            language = self._get_language_from_request()
            language_name = self._get_language_name(language)
            
            self.logger.info(f"Request recibido:")
            self.logger.info(f"- Archivo: {file.filename}")
            self.logger.info(f"- Idioma: {language} ({language_name})")
            
            # Extraer texto del archivo
            extracted_text = self.file_processor.process_file(file_content, file.filename)
            self.logger.info(f"Texto extraído: {len(extracted_text)} caracteres")
            self.logger.info(f"- Contenido original: '{extracted_text[:100]}{'...' if len(extracted_text) > 100 else ''}'")
            
            # Anonimizar texto extraído
            anonymized_text = self.presidio_service.anonymize_text(extracted_text, language=language)
            
            self.logger.info("Resultado de la anonimización:")
            self.logger.info(f"- Longitud del texto anonimizado: {len(anonymized_text)} caracteres")
            self.logger.info(f"- Contenido anonimizado: '{anonymized_text[:100]}{'...' if len(anonymized_text) > 100 else ''}'")
            
            response = {
                'filename': file.filename,
                'original_text': extracted_text,
                'anonymized_text': anonymized_text,
                'language': language,
                'language_name': language_name
            }
            
            return jsonify(response)
        except Exception as e:
            self.logger.error(f"Error anonimizando archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def health(self):
        """Endpoint de salud"""
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /health (Estado del Servicio)")
        self.logger.info("=" * 50)
        
        # Crear un diccionario que mapea códigos de idioma a nombres descriptivos
        languages_info = {code: self._get_language_name(code) for code in self.supported_languages}
        
        self.logger.info(f"Estado del servicio: ACTIVO")
        self.logger.info(f"Idiomas soportados: {languages_info}")
        
        return jsonify({
            'status': 'healthy', 
            'service': 'Presidio API',
            'supported_languages': self.supported_languages,
            'language_names': languages_info
        })
    
    def preview_anonymization_text(self):
        """
        Endpoint para previsualizar qué palabras serán anonimizadas en texto sin realizar la anonimización.
        Acepta únicamente texto y devuelve las entidades detectadas con su contexto.
        """
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /preview-anonymization-text (Previsualización Texto)")
        self.logger.info("=" * 50)
        
        try:
            text = None
            language = self.default_language  # Valor predeterminado
            
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
                        language = self._get_language_from_request(data)
                    else:
                        self.logger.error("Falta el campo 'text' en el JSON")
                        return jsonify({'error': 'Se requiere el campo "text" en el JSON para previsualización'}), 400
                except Exception as e:
                    self.logger.error(f"Error al procesar JSON: {str(e)}")
                    return jsonify({'error': f'Error al procesar JSON: {str(e)}'}), 400
            
            # Para solicitudes form-urlencoded
            elif request.form and 'text' in request.form:
                self.logger.info("Procesando texto desde formulario")
                text = request.form.get('text')
                language = self._get_language_from_request()
            
            # Si no se reconoce el formato, pero hay datos
            else:
                # Intentar procesar como JSON sin importar el Content-Type
                try:
                    data = request.get_json(force=True, silent=True)
                    if data and 'text' in data:
                        self.logger.info("Forzando procesamiento como JSON")
                        text = data['text']
                        language = self._get_language_from_request(data)
                    else:
                        self.logger.error("No se encontró texto para previsualización")
                        return jsonify({
                            'error': 'No se encontró texto para previsualización',
                            'content_type': content_type,
                            'tip': 'Envíe un objeto JSON con el campo "text" o use form-urlencoded'
                        }), 400
                except Exception:
                    self.logger.error("No se pudo interpretar la solicitud")
                    return jsonify({
                        'error': 'No se pudo interpretar la solicitud. Content-Type incorrecto o datos malformados',
                        'content_type_recibido': content_type,
                        'tip': 'Use application/json con un campo "text" o form-urlencoded'
                    }), 400
            
            if not text:
                self.logger.error("No se proporcionó texto para analizar")
                return jsonify({'error': 'No se proporcionó texto para analizar'}), 400
            
            language_name = self._get_language_name(language)
            self.logger.info(f"Analizando texto para previsualización:")
            self.logger.info(f"- Idioma: {language} ({language_name})")
            self.logger.info(f"- Longitud del texto: {len(text)} caracteres")
            self.logger.info(f"- Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            # Analizar el texto para detectar entidades
            analysis_results = self.presidio_service.analyze_text(text, language=language)
            
            # Enriquecer los resultados con el texto original de cada entidad
            for result in analysis_results:
                result['texto_original'] = text[result['start']:result['end']]
            
            self.logger.info("Resultados de la previsualización:")
            self.logger.info(f"- Total entidades encontradas: {len(analysis_results)}")
            for idx, entity in enumerate(analysis_results[:5]):  # Limitar a 5 para no saturar los logs
                self.logger.info(f"  Entidad {idx+1}: {entity['entity_type']} - '{entity['texto_original']}' (score: {entity['score']:.2f})")
            if len(analysis_results) > 5:
                self.logger.info(f"  ... y {len(analysis_results)-5} entidades más")
            
            # Preparar la respuesta
            response = {
                'fuente': 'text',
                'texto_completo': text,
                'entidades_detectadas': analysis_results,
                'total_entidades': len(analysis_results),
                'idioma': language,
                'nombre_idioma': language_name
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
        self.logger.info("=" * 50)
        self.logger.info("ENDPOINT: /preview-anonymization-file (Previsualización Archivo)")
        self.logger.info("=" * 50)
        
        try:
            # Verificar si se envió un archivo
            if 'file' not in request.files:
                self.logger.error("No se proporcionó archivo")
                return jsonify({'error': 'No se proporcionó archivo'}), 400
                
            file = request.files['file']
            if file.filename == '':
                self.logger.error("No se seleccionó ningún archivo")
                return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
            
            file_content = file.read()
            language = self._get_language_from_request()
            language_name = self._get_language_name(language)
            
            # Procesar el archivo según su tipo
            self.logger.info(f"Procesando archivo para previsualización:")
            self.logger.info(f"- Nombre del archivo: {file.filename}")
            self.logger.info(f"- Idioma: {language} ({language_name})")
            
            try:
                text = self.file_processor.process_file(file_content, file.filename)
                if not text:
                    self.logger.error("No se pudo extraer texto del archivo")
                    return jsonify({'error': 'No se pudo extraer texto del archivo'}), 400
                
                self.logger.info(f"- Texto extraído: {len(text)} caracteres")
                self.logger.info(f"- Contenido: '{text[:100]}{'...' if len(text) > 100 else ''}'")
                
            except Exception as e:
                self.logger.error(f"Error al procesar el archivo: {str(e)}")
                return jsonify({'error': f'Error al procesar el archivo: {str(e)}'}), 400
            
            # Analizar el texto para detectar entidades
            analysis_results = self.presidio_service.analyze_text(text, language=language)
            
            # Enriquecer los resultados con el texto original de cada entidad
            for result in analysis_results:
                result['texto_original'] = text[result['start']:result['end']]
            
            self.logger.info("Resultados de la previsualización:")
            self.logger.info(f"- Total entidades encontradas: {len(analysis_results)}")
            for idx, entity in enumerate(analysis_results[:5]):  # Limitar a 5 para no saturar los logs
                self.logger.info(f"  Entidad {idx+1}: {entity['entity_type']} - '{entity['texto_original']}' (score: {entity['score']:.2f})")
            if len(analysis_results) > 5:
                self.logger.info(f"  ... y {len(analysis_results)-5} entidades más")
            
            # Preparar la respuesta
            response = {
                'fuente': 'file',
                'nombre_archivo': file.filename,
                'texto_completo': text,
                'entidades_detectadas': analysis_results,
                'total_entidades': len(analysis_results),
                'idioma': language,
                'nombre_idioma': language_name
            }
                
            return jsonify(response)
            
        except Exception as e:
            self.logger.error(f"Error en previsualización de archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500