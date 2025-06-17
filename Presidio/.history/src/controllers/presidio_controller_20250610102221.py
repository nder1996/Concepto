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
        app.add_url_rule('/anonymize-specific-entities', 'anonymize_specific_entities_endpoint', self.anonymize_specific_entities_endpoint, methods=['POST'])
        app.add_url_rule('/anonymize-specific-entities-file', 'anonymize_specific_entities_file', self.anonymize_specific_entities_file, methods=['POST'])
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
    
    def preview_anonymization_text(self):
        """
        Endpoint para previsualizar qué palabras serán anonimizadas en texto sin realizar la anonimización.
        Acepta únicamente texto y devuelve las entidades detectadas con su contexto.
        """
        self.logger.info("Iniciando previsualización de anonimización de texto")
        try:
            text = None
            language = 'en'  # Valor predeterminado
            
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
                        language = data.get('language', 'en')
                    else:
                        return jsonify({'error': 'Se requiere el campo "text" en el JSON para previsualización'}), 400
                except Exception as e:
                    return jsonify({'error': f'Error al procesar JSON: {str(e)}'}), 400
            
            # Para solicitudes form-urlencoded
            elif request.form and 'text' in request.form:
                self.logger.info("Procesando texto desde formulario")
                text = request.form.get('text')
                language = request.form.get('language', 'en')
            
            # Si no se reconoce el formato, pero hay datos
            else:
                # Intentar procesar como JSON sin importar el Content-Type
                try:
                    data = request.get_json(force=True, silent=True)
                    if data and 'text' in data:
                        self.logger.info("Forzando procesamiento como JSON")
                        text = data['text']
                        language = data.get('language', 'en')
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
            language = request.form.get('language', 'en')
            
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
      def anonymize_specific_entities_endpoint(self):
        """
        Endpoint para anonimizar solo entidades específicas con umbrales de confianza personalizados
        """
        self.logger.info("Iniciando anonimización específica de texto")
        try:
            # Obtener datos de la solicitud
            data = request.json
            text = data['text']
            language = data.get('language', 'en')
            custom_thresholds = data.get('thresholds', None)
            
            # Validar los umbrales personalizados si se proporcionan
            if custom_thresholds:
                if not isinstance(custom_thresholds, dict):
                    return jsonify({'error': 'El parámetro "thresholds" debe ser un diccionario'}), 400
                
                # Validar que los valores sean números entre 0 y 1
                for entity_type, threshold in custom_thresholds.items():
                    try:
                        threshold_value = float(threshold)
                        if threshold_value < 0 or threshold_value > 1:
                            return jsonify({'error': f'El umbral para {entity_type} debe estar entre 0 y 1'}), 400
                    except (ValueError, TypeError):
                        return jsonify({'error': f'El umbral para {entity_type} debe ser un número'}), 400
            
            self.logger.info(f"Anonimizando entidades específicas en texto de {len(text)} caracteres (idioma: {language})")
            if custom_thresholds:
                self.logger.info(f"Umbrales personalizados: {custom_thresholds}")
            
            # Primero intentar analizar el texto para ver si se encuentran entidades
            analyze_results = self.presidio_service.analyze_text(text, language=language)
            
            # Verificar si hay resultados de entidades en general
            if not analyze_results:
                self.logger.warning("No se encontraron entidades en el texto durante el análisis previo")
                return jsonify({
                    'original_text': text,
                    'anonymized_text': text,
                    'warning': 'No se encontraron entidades para anonimizar en el texto proporcionado',
                    'suggestion': 'Verifica que el texto contenga información personal o prueba con otro idioma'
                })
            
            # Verificar si hay entidades del tipo solicitado 
            if custom_thresholds:
                entity_types_found = {result['entity_type'] for result in analyze_results}
                requested_types = set(custom_thresholds.keys())
                matching_types = entity_types_found.intersection(requested_types)
                
                if not matching_types:
                    self.logger.warning(f"No se encontraron entidades de los tipos solicitados: {requested_types}")
                    return jsonify({
                        'original_text': text,
                        'anonymized_text': text,
                        'warning': 'No se encontraron entidades de los tipos solicitados',
                        'entidades_disponibles': list(entity_types_found),
                        'entidades_solicitadas': list(requested_types),
                        'suggestion': 'Prueba con alguna de las entidades disponibles en el texto'
                    })
            
            # Realizar la anonimización específica
            anonymized_text = self.presidio_service.anonymize_specific_entities(
                text=text,
                language=language,
                custom_thresholds=custom_thresholds
            )
            
            # Verificar si el texto fue anonimizado o no cambió
            if anonymized_text == text:
                self.logger.warning("El texto no fue anonimizado, posiblemente no se detectaron entidades que superen el umbral de confianza")
                
                # Encontrar las entidades detectadas y sus umbrales
                entity_info = []
                for result in analyze_results:
                    entity_type = result['entity_type']
                    if custom_thresholds and entity_type in custom_thresholds:
                        threshold = custom_thresholds[entity_type]
                        entity_info.append({
                            'tipo': entity_type,
                            'texto': text[result['start']:result['end']],
                            'puntaje': result['score'],
                            'umbral_requerido': threshold,
                            'cumple_umbral': result['score'] >= threshold
                        })
                
                return jsonify({
                    'original_text': text,
                    'anonymized_text': text,
                    'warning': 'El texto no se anonimizó porque ninguna entidad cumplió con los umbrales de confianza',
                    'entidades_detectadas': entity_info,
                    'suggestion': 'Prueba disminuyendo los umbrales de confianza para permitir más coincidencias'
                })
            
            self.logger.info("Anonimización específica completada exitosamente")
            
            # Devolver el resultado normal
            return jsonify({
                'original_text': text,
                'anonymized_text': anonymized_text
            })
            
        except Exception as e:
            self.logger.error(f"Error en anonimización específica: {str(e)}")
            return jsonify({
                'error': f"Error en la anonimización: {str(e)}",
                'suggestion': 'Verifica el formato de los datos y que el idioma sea compatible'
            }), 500
    
    def anonymize_specific_entities_file(self):
        """
        Endpoint para anonimizar solo entidades específicas en archivos con umbrales de confianza personalizados
        """
        self.logger.info("Iniciando anonimización específica de archivo")
        try:
            # Verificar si se envió un archivo
            if 'file' not in request.files:
                return jsonify({'error': 'No se proporcionó archivo'}), 400
            
            # Obtener archivo y parámetros
            file = request.files['file']
            file_content = file.read()
            language = request.form.get('language', 'en')
            
            # Procesar umbrales personalizados si se proporcionan
            custom_thresholds = None
            if 'thresholds' in request.form:
                import json
                try:
                    custom_thresholds = json.loads(request.form['thresholds'])
                    if not isinstance(custom_thresholds, dict):
                        return jsonify({'error': 'El parámetro "thresholds" debe ser un diccionario válido en formato JSON'}), 400
                    
                    # Validar que los valores sean números entre 0 y 1
                    for entity_type, threshold in custom_thresholds.items():
                        try:
                            threshold_value = float(threshold)
                            if threshold_value < 0 or threshold_value > 1:
                                return jsonify({'error': f'El umbral para {entity_type} debe estar entre 0 y 1'}), 400
                        except (ValueError, TypeError):
                            return jsonify({'error': f'El umbral para {entity_type} debe ser un número'}), 400
                except json.JSONDecodeError:
                    return jsonify({'error': 'El formato del parámetro "thresholds" no es un JSON válido'}), 400
            
            self.logger.info(f"Procesando archivo para anonimización específica: {file.filename}")
            if custom_thresholds:
                self.logger.info(f"Umbrales personalizados: {custom_thresholds}")
            
            # Extraer texto del archivo
            extracted_text = self.file_processor.process_file(file_content, file.filename)
            self.logger.info(f"Texto extraído: {len(extracted_text)} caracteres")
            
            # Realizar la anonimización específica
            anonymized_text = self.presidio_service.anonymize_specific_entities(
                text=extracted_text,
                language=language,
                custom_thresholds=custom_thresholds
            )
            
            self.logger.info("Anonimización específica de archivo completada")
            
            # Devolver el resultado
            return jsonify({
                'filename': file.filename,
                'original_text': extracted_text,
                'anonymized_text': anonymized_text
            })
            
        except Exception as e:
            self.logger.error(f"Error en anonimización específica de archivo: {str(e)}")
            return jsonify({'error': str(e)}), 500