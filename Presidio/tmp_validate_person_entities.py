    def validate_person_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        """
        Valida las entidades de tipo PERSON utilizando múltiples métodos:
        1. Reconocedor predeterminado de Presidio con umbral muy bajo
        2. Detección de patrones de palabras capitalizadas como posibles nombres
        3. Validación con Flair para confirmar si realmente son nombres de persona
        
        Args:
            text: Texto a analizar
            language: Idioma del texto (es, en)
            
        Returns:
            List[Dict[str, Any]]: Lista de entidades validadas con información detallada
        """
        import re
        
        # Validar y normalizar el idioma
        language = language.lower() if language else self.default_language
        if language not in self.supported_languages:
            self.logger.warning(
                f"Idioma no soportado: {language}. Usando idioma predeterminado: {self.default_language}"
            )
            language = self.default_language
            
        # Obtener umbrales específicos para el idioma
        thresholds = self.get_entity_thresholds(language)
        person_threshold = 0.05  # Umbral extremadamente bajo para Presidio
        
        # Lista para almacenar todas las entidades candidatas encontradas por cualquier método
        all_candidates = []
        
        # Seleccionar el analizador específico para el idioma
        analyzer = self.analyzers.get(language)
        if not analyzer:
            self.logger.error(f"No se encontró un analizador para el idioma: {language}")
            return []
            
        # Registrar análisis inicial
        self.logger.info(f"Detectando nombres de personas en texto: '{text[:50]}...' en idioma: {language}")
        self.logger.info(f"Usando métodos múltiples para detección de nombres (Presidio + patrones + Flair)")
        
        # ------------------------------------------------------------------------
        # MÉTODO 1: UTILIZAR PRESIDIO CON UMBRAL MUY BAJO
        # ------------------------------------------------------------------------
        
        # Analizar el texto específicamente para entidades de tipo PERSON
        presidio_results = analyzer.analyze(text=text, language=language, entities=["PERSON"])
        self.logger.info(f"Total de nombres detectados por Presidio: {len(presidio_results)}")
        
        # Agregar los resultados de Presidio a los candidatos si superan el umbral mínimo
        for r in presidio_results:
            if r.entity_type == "PERSON" and r.score >= person_threshold:
                name_text = text[r.start:r.end].strip()
                self.logger.info(f"Candidato Presidio: '{name_text}', Score: {r.score}")
                
                # Extraer contexto para validación Flair
                inicio_contexto = max(0, r.start - 50)
                fin_contexto = min(len(text), r.end + 50)
                contexto = text[inicio_contexto:fin_contexto]
                
                all_candidates.append({
                    "entity_type": "PERSON",
                    "nombre": name_text,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "language": language,
                    "contexto": contexto,
                    "metodo": "presidio"
                })
        
        # ------------------------------------------------------------------------
        # MÉTODO 2: BUSCAR PATRONES DE POSIBLES NOMBRES
        # ------------------------------------------------------------------------
        
        # Patrones que pueden indicar nombres de personas en español
        # - Secuencia de 2-4 palabras capitalizadas
        # - Palabras como "compañero", "señor", "señora", etc. seguidas de palabras capitalizadas
        
        # Dividir el texto en segmentos para análisis
        segments = re.split(r'[,.:;()\[\]{}"\']', text)
        
        for segment in segments:
            # Buscar secuencias de palabras capitalizadas (posibles nombres completos)
            words = segment.strip().split()
            capitalized_sequences = []
            current_sequence = []
            
            for word in words:
                # Si la palabra empieza con mayúscula y no es principio de oración
                if word and word[0].isupper() and len(word) > 1:
                    # Si es una palabra que típicamente no forma parte de nombres (artículos, etc.)
                    if word.lower() in ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del']:
                        # Solo seguir si ya se inició una secuencia
                        if current_sequence:
                            current_sequence.append(word)
                    else:
                        current_sequence.append(word)
                else:
                    # Si tenemos una secuencia, guardarla si tiene al menos 2 palabras
                    if len(current_sequence) >= 2:
                        capitalized_sequences.append(" ".join(current_sequence))
                    current_sequence = []
            
            # No olvidar la última secuencia
            if len(current_sequence) >= 2:
                capitalized_sequences.append(" ".join(current_sequence))
            
            # También buscar patrones como "compañero [Nombre]"
            indicadores_nombre = [
                r'compañero[s]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'compañera[s]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'señor[a]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'colega[s]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'doctor[a]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'licenciado[a]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'ingeniero[a]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})',
                r'junto\s+[a|con]?\s+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})'
            ]
            
            for pattern in indicadores_nombre:
                matches = re.finditer(pattern, segment, re.IGNORECASE)
                for match in matches:
                    if match.group(1) not in capitalized_sequences:
                        capitalized_sequences.append(match.group(1))
            
            # Procesar las secuencias encontradas en este segmento
            for seq in capitalized_sequences:
                # Encontrar la posición en el texto original
                start_pos = text.find(seq)
                if start_pos != -1:
                    end_pos = start_pos + len(seq)
                    
                    # Extraer contexto
                    inicio_contexto = max(0, start_pos - 50)
                    fin_contexto = min(len(text), end_pos + 50)
                    contexto = text[inicio_contexto:fin_contexto]
                    
                    # Calcular un score basado en características heurísticas
                    heuristic_score = 0.5  # Score base
                    
                    # Más palabras, mayor probabilidad de ser un nombre completo
                    num_words = len(seq.split())
                    if num_words >= 3:
                        heuristic_score += 0.2
                    
                    # Secuencias demasiado largas son menos probables de ser nombres
                    if len(seq) > 30:
                        heuristic_score -= 0.1
                    
                    # Añadir a la lista de candidatos
                    all_candidates.append({
                        "entity_type": "PERSON",
                        "nombre": seq,
                        "start": start_pos,
                        "end": end_pos,
                        "score": heuristic_score,
                        "language": language,
                        "contexto": contexto,
                        "metodo": "patron"
                    })
                    self.logger.info(f"Candidato por patrón: '{seq}', Score: {heuristic_score}")
        
        # ------------------------------------------------------------------------
        # CONSOLIDAR CANDIDATOS Y ELIMINAR DUPLICADOS/SOLAPAMIENTOS
        # ------------------------------------------------------------------------
        
        # Ordenar por posición en el texto
        all_candidates.sort(key=lambda x: x["start"])
        
        # Eliminar solapamientos, quedándonos con el candidato más largo
        consolidated_candidates = []
        i = 0
        while i < len(all_candidates):
            current = all_candidates[i]
            
            # Buscar solapamientos con candidatos siguientes
            j = i + 1
            overlapping = False
            
            while j < len(all_candidates):
                next_candidate = all_candidates[j]
                
                # Si hay solapamiento
                if current["end"] > next_candidate["start"]:
                    # Si el siguiente candidato es más largo, nos quedamos con él
                    if (next_candidate["end"] - next_candidate["start"]) > (current["end"] - current["start"]):
                        current = next_candidate
                    j += 1
                    overlapping = True
                else:
                    break
            
            # Si encontramos solapamientos, saltamos los candidatos solapados
            if overlapping:
                i = j
            else:
                i += 1
                
            consolidated_candidates.append(current)
        
        self.logger.info(f"Total de candidatos consolidados: {len(consolidated_candidates)}")
        
        # ------------------------------------------------------------------------
        # MÉTODO 3: VALIDAR CON FLAIR PARA CONFIRMAR NOMBRES REALES
        # ------------------------------------------------------------------------
        
        # Lista para almacenar entidades validadas
        validated_results = []
        
        # Verificar si Flair está disponible
        if FLAIR_DISPONIBLE and consolidated_candidates:
            self.logger.info("⭐ Aplicando validación con Flair...")
            try:
                # Crear una instancia del validador Flair
                validador_flair = FlairContextValidator(umbral_confianza=0.65)  # Umbral intermedio
                
                # Validar los candidatos con Flair
                for candidato in consolidated_candidates:
                    nombre = candidato["nombre"]
                    contexto = candidato["contexto"]
                    start = candidato["start"]
                    end = candidato["end"]
                    
                    resultado_validacion = validador_flair.validar_nombre(
                        texto=text, 
                        nombre=nombre, 
                        contexto=contexto,
                        start=start, 
                        end=end
                    )
                    
                    if resultado_validacion["es_valido"]:
                        # Es un nombre válido según Flair
                        validated_results.append({
                            "entity_type": "PERSON",
                            "start": start,
                            "end": end,
                            "score": resultado_validacion["confianza"],
                            "language": language,
                        })
                        self.logger.info(f"✅ Nombre validado por Flair: '{resultado_validacion['nombre_normalizado']}', " +
                                         f"Score: {resultado_validacion['confianza']}, " +
                                         f"Método original: {candidato['metodo']}")
                    else:
                        # Para los candidatos detectados por Presidio con score alto, incluirlos aunque Flair los rechace
                        if candidato["metodo"] == "presidio" and candidato["score"] > 0.8:
                            validated_results.append({
                                "entity_type": "PERSON",
                                "start": start,
                                "end": end,
                                "score": candidato["score"],
                                "language": language,
                            })
                            self.logger.info(f"✅ Nombre aceptado por score alto de Presidio aunque rechazado por Flair: '{nombre}', " +
                                            f"Score: {candidato['score']}")
                        else:
                            self.logger.info(f"❌ Descartado por Flair: '{nombre}' - Motivo: {resultado_validacion['motivo']}")
                
                self.logger.info(f"Total de nombres validados por Flair: {len(validated_results)}")
                
            except Exception as e:
                self.logger.error(f"Error en validación con Flair: {str(e)}")
                # Si falla Flair, usamos los candidatos consolidados como fallback
                self.logger.info("Usando candidatos consolidados como fallback por error en Flair")
                for c in consolidated_candidates:
                    if c["score"] >= 0.5:  # Un umbral mínimo para fallback
                        validated_results.append({
                            "entity_type": c["entity_type"],
                            "start": c["start"],
                            "end": c["end"],
                            "score": c["score"],
                            "language": c["language"],
                        })
                        self.logger.info(f"✅ Nombre aceptado como fallback: '{c['nombre']}', Score: {c['score']}")
        else:
            # Si no hay validador Flair disponible, usar candidatos consolidados con filtrado básico
            if not FLAIR_DISPONIBLE:
                self.logger.info("⚠️ Validador Flair no disponible, usando filtrado básico")
            
            for c in consolidated_candidates:
                # Aplicar un filtrado simple por score, dependiendo del método de detección
                threshold = 0.3 if c["metodo"] == "presidio" else 0.5
                if c["score"] >= threshold:
                    validated_results.append({
                        "entity_type": c["entity_type"],
                        "start": c["start"],
                        "end": c["end"],
                        "score": c["score"],
                        "language": c["language"],
                    })
                    self.logger.info(f"✅ Nombre aceptado por filtrado básico: '{c['nombre']}', " + 
                                     f"Score: {c['score']}, Método: {c['metodo']}")
        
        self.logger.info(f"Total de nombres validados después del proceso completo: {len(validated_results)}")
        return validated_results
