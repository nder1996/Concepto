from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
import re
from typing import List, Optional, Tuple
from presidio_analyzer.nlp_engine import NlpArtifacts
from src.config.settings import SUPPORTED_ENTITY_TYPES

class EmailRecognizer(PatternRecognizer):
    """
    Reconocedor personalizado para direcciones de correo electrónico.
    
    Este reconocedor utiliza expresiones regulares avanzadas para detectar direcciones 
    de correo electrónico con alta precisión, evitando falsos positivos y soportando
    formatos internacionales.
    """
    
    # Identificadores para el reconocedor
    ENTITY = "EMAIL_ADDRESS" # Debe coincidir con un tipo en SUPPORTED_ENTITY_TYPES
    
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
            
        # Patrón de comunicación simplificado
        if re.search(r'(escr[ií]b|env[ií]a).{0,20}(a|@).{0,30}' + re.escape(email_text),
                    context_text, re.IGNORECASE):
            score += 0.1
            
        return min(0.3, score)
        
    def validate_result(self, pattern_text: str) -> bool:
        """
        Valida que el texto coincidente realmente tenga formato de email.
        
        Args:
            pattern_text (str): El texto del correo electrónico a validar
            
        Returns:
            bool: True si parece un email válido
        """
        # Validación más estricta que el patrón inicial
        if '@' not in pattern_text:
            return False
            
        local_part, domain_part = pattern_text.split('@', 1)
        
        # Verificaciones básicas
        if not local_part or not domain_part:
            return False
        
        # El dominio debe tener al menos un punto
        if '.' not in domain_part:
            return False
            
        # La última parte del dominio debe tener al menos 2 caracteres
        tld = domain_part.split('.')[-1]
        if not tld or len(tld) < 2:
            return False
            
        return True
        
    def analyze(
        self, pattern_text: str, context: str = None, nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """
        Analiza el texto para detectar emails y devuelve resultados con puntaje
        enriquecido según características y contexto.
        
        Args:
            pattern_text (str): El texto donde buscar emails
            context (str, optional): Contexto. Defaults to None.
            nlp_artifacts (NlpArtifacts, optional): Artefactos NLP. Defaults to None.
            
        Returns:
            List[RecognizerResult]: Lista de resultados de reconocimiento
        """
        # Usar el análisis base de la clase padre
        results = super().analyze(pattern_text, context, nlp_artifacts)
        
        # Enriquecer cada resultado
        for result in results:
            # Extraer el texto coincidente
            matched_text = pattern_text[result.start:result.end]
            
            # Validación adicional
            if not self.validate_result(matched_text):
                continue
                
            # Mejorar el score según características del email
            signature_score = self.enhance_signature_score(matched_text)
            
            # Mejorar score según contexto si está disponible
            context_score = 0.0
            if context:
                context_score = self.analyze_email_context(context, matched_text)
                
            # Aumentar el score final (sin exceder 1.0)
            result.score = min(1.0, result.score + signature_score + context_score)
            
        return results
