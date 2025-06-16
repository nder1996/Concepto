"""
Script de prueba para validar los reconocedores personalizados
"""
import sys
import os

# Añadir el directorio raíz al path para permitir importar los módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.presidio.recognizers import EmailRecognizer, PhoneRecognizer, ColombianIDRecognizer
try:
    from src.services.presidio.recognizers import FlairContextValidator
    HAS_FLAIR = True
except ImportError:
    HAS_FLAIR = False

def test_email_recognizer():
    """Prueba el reconocedor de correos electrónicos"""
    print("\n== Probando EmailRecognizer ==")
    recognizer = EmailRecognizer(supported_language="es")
    
    test_cases = [
        "Mi correo es usuario@example.com y pueden contactarme ahí.",
        "El email oficial es soporte.tecnico@empresa-grande.com.co",
        "Este no es un correo: usuario@invalido"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nPrueba {i}: '{text}'")
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        registry = RecognizerRegistry()
        registry.add_recognizer(recognizer)
        analyzer = AnalyzerEngine(registry=registry)
        results = analyzer.analyze(text=text, language="es")
        
        if results:
            for result in results:
                print(f"- Detectado: '{text[result.start:result.end]}' (score: {result.score:.2f})")
        else:
            print("- No se detectaron correos")

def test_phone_recognizer():
    """Prueba el reconocedor de números telefónicos"""
    print("\n== Probando PhoneRecognizer ==")
    recognizer = PhoneRecognizer(supported_language="es")
    
    test_cases = [
        "Mi número es 320 123 4567 y me pueden llamar en horario laboral.",
        "El teléfono fijo es (1) 601 7890 ext 123.",
        "Para soporte: +57 300 987 6543",
        "Este no es un teléfono: 12345"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nPrueba {i}: '{text}'")
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        registry = RecognizerRegistry()
        registry.add_recognizer(recognizer)
        analyzer = AnalyzerEngine(registry=registry)
        results = analyzer.analyze(text=text, language="es")
        
        if results:
            for result in results:
                print(f"- Detectado: '{text[result.start:result.end]}' (score: {result.score:.2f})")
        else:
            print("- No se detectaron teléfonos")

def test_colombian_id_recognizer():
    """Prueba el reconocedor de documentos colombianos"""
    print("\n== Probando ColombianIDRecognizer ==")
    recognizer = ColombianIDRecognizer(supported_language="es")
    
    test_cases = [
        "Mi cédula es 1234567890",
        "CC 98.765.432",
        "Tarjeta de identidad: 1098765432",
        "Este no es una cédula: ABCDE12345"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nPrueba {i}: '{text}'")
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        registry = RecognizerRegistry()
        registry.add_recognizer(recognizer)
        analyzer = AnalyzerEngine(registry=registry)
        results = analyzer.analyze(text=text, language="es")
        
        if results:
            for result in results:
                print(f"- Detectado: '{text[result.start:result.end]}' (score: {result.score:.2f})")
        else:
            print("- No se detectaron documentos")

if __name__ == "__main__":
    print("== PRUEBAS DE RECONOCEDORES PERSONALIZADOS ==")
    
    # Reconocedores instalados
    print("\nReconocedores disponibles:")
    print("- EmailRecognizer ✓")
    print("- PhoneRecognizer ✓")
    print("- ColombianIDRecognizer ✓")
    print(f"- FlairContextValidator {'✓' if HAS_FLAIR else '✗'}")
    
    # Ejecutar pruebas
    test_email_recognizer()
    test_phone_recognizer()
    test_colombian_id_recognizer()
    
    print("\n== PRUEBAS COMPLETADAS ==")
