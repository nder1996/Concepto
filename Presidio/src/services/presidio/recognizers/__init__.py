"""
Módulo que contiene todos los reconocedores personalizados utilizados por el servicio de reconocimiento de entidades.

Este módulo está diseñado como un punto centralizado de acceso a todos los reconocedores personalizados,
facilitando su importación desde diferentes partes de la aplicación.

Reconocedores disponibles:
- EmailRecognizer: Reconocedor personalizado para direcciones de correo electrónico
- PhoneRecognizer: Reconocedor personalizado para números telefónicos colombianos e internacionales
- ColombianIDRecognizer: Reconocedor personalizado para documentos de identidad colombianos
"""

# Exportar los reconocedores para facilitar su importación desde otras partes del código
from .recognizer_email import EmailRecognizer
from .recognizer_phone import PhoneRecognizer
from .recognizer_co_identity_number import ColombianIDRecognizer

# También exportamos el validador de Flair si está disponible
try:
    # Renombramos la clase para mantener compatibilidad con código existente
    from .flair_validator import FlairContextValidator
    __all__ = ['EmailRecognizer', 'PhoneRecognizer', 'ColombianIDRecognizer', 'FlairContextValidator']
except ImportError:
    __all__ = ['EmailRecognizer', 'PhoneRecognizer', 'ColombianIDRecognizer']
