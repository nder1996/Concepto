from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple
from presidio_analyzer.nlp_engine import NlpArtifacts

class EmailRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para direcciones de correo electrónico.
    
    Este reconocedor utiliza expresiones regulares avanzadas para detectar direcciones 
    de correo electrónico con alta precisión, evitando falsos positivos y soportando
    formatos internacionales.
    """
    
    # Identificadores para el reconocedor
    ENTITY = "EMAIL_ADDRESS"
    
    # Patrones regex simplificados pero efectivos
    SIMPLE_EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = None,
        name: str = None,
    ):
        # Definir patrones de detección simplificados
        patterns = [
            Pattern(
                name="email_simple",
                regex=self.SIMPLE_EMAIL_PATTERN,
                score=0.7,
            )
        ]
        
        # Inicializar con valores por defecto
        context = context if context else []
        name = name if name else "EmailRecognizer"
        supported_entity = supported_entity if supported_entity else self.ENTITY
        
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def enhance_signature_score(self, pattern_text: str) -> float:
        """
        Mejora el score basado en características del email.
        
        Args:
            pattern_text (str): El texto del correo electrónico detectado
            
        Returns:
            float: Score adicional entre 0 y 0.3
        """
        score_adjustment = 0.0
        
        # Verificar formato básico
        if '@' not in pattern_text:
            return 0.0
        
        local_part, domain_part = pattern_text.split('@', 1)
        
        # Verificaciones simplificadas de la parte local
        if 2 <= len(local_part) <= 64:
            score_adjustment += 0.1
        
        # Verificaciones simplificadas del dominio
        if domain_part and '.' in domain_part:
            domain_parts = domain_part.split('.')
            if len(domain_parts) >= 2 and 2 <= len(domain_parts[-1]) <= 6:
                score_adjustment += 0.1
        
        return score_adjustment
        
    def analyze_email_context(self, context_text: str, email_text: str) -> float:
        """
        Analiza el contexto alrededor de un correo electrónico.
        
        Args:
            context_text (str): Texto de contexto alrededor del email
            email_text (str): El correo electrónico detectado
            
        Returns:
            float: Score adicional entre 0 y 0.3
        """
        score = 0.0
        
        # Patrones de contexto simplificados
        if re.search(r'(correo|email|e-mail|mail)\s*:?\s*' + re.escape(email_text), 
                    context_text, re.IGNORECASE):
            score += 0.2
        
        # Patrón de contacto simplificado
        if re.search(r'contact[oa][rme]?\s.{0,30}' + re.escape(email_text), 
                    context_text, re.IGNORECASE):
            score += 0.1
            
        return min(0.3, score)
    
    def analyze(self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None) -> List[RecognizerResult]:
        """
        Analiza el texto para encontrar correos electrónicos.
        
        Args:
            text (str): El texto a analizar
            entities (List[str]): Lista de entidades a buscar
            nlp_artifacts (NlpArtifacts): Artefactos NLP opcionales
            
        Returns:
            List[RecognizerResult]: Lista de resultados del reconocedor
        """
        # Obtenemos los resultados base mediante patrones
        results = super().analyze(text, entities, nlp_artifacts)
        
        enhanced_results = []
        for result in results:
            # Extraer el texto del correo detectado
            start, end = result.start, result.end
            email_text = text[start:end]
            
            # Contexto simplificado (10 caracteres antes y después)
            context_start = max(0, start - 10)
            context_end = min(len(text), end + 10)
            context_text = text[context_start:context_end]
            
            # Calcular scores adicionales
            base_score = self.enhance_signature_score(email_text)
            context_score = self.analyze_email_context(context_text, email_text)
            
            # Combinar scores
            enhanced_score = min(1.0, result.score + base_score + context_score)
            
            # Crear resultado mejorado
            enhanced_result = RecognizerResult(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=enhanced_score,
                analysis_explanation=result.analysis_explanation
            )
            enhanced_results.append(enhanced_result)
            
        return enhanced_results
        
    def validate_result(self, pattern_match) -> Tuple[bool, float]:
        """
        Validación adicional para reducir falsos positivos.
        
        Args:
            pattern_match: El match del patrón
            
        Returns:
            Tuple[bool, float]: (es_válido, score_ajustado)
        """
        # Verificar si pattern_match es un objeto Match
        try:
            # Si es un objeto Match, obtener el texto del match
            if hasattr(pattern_match, 'group'):
                match_text = pattern_match.group(0)
            # Si es un string, usarlo directamente
            elif isinstance(pattern_match, str):
                match_text = pattern_match
            else:
                return False, 0.0
                
            # Verificaciones básicas
            if '@' not in match_text:
                return False, 0.0
                
            # Verificar caracteres inválidos
            if re.search(r'[\s\(\)\[\]\{\}<>\\"]', match_text):
                return False, 0.0
                
            # Verificar longitud
            if len(match_text) < 6 or len(match_text) > 254:
                return False, 0.0
            
            # Verificar dominio simplificado
            domain = match_text.split('@')[-1]
            if not ('.' in domain):
                return False, 0.0
            
            return True, 0.7
            
        except Exception:
            # En caso de cualquier error, considerar inválido
            return False, 0.0