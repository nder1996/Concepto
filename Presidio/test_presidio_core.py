"""
Script de prueba para el servicio core de Presidio.
Este script demuestra el uso básico del servicio core y el orquestador.
"""

from src.services.presidio.core_presidio_service import CorePresidioService
from src.services.presidio.presidio_orchestrator import PresidioOrchestrator

def test_presidio_core():
    """Prueba el servicio core de Presidio directamente."""
    print("=== PRUEBA DEL SERVICIO CORE DE PRESIDIO ===")
    
    # Crear instancia del servicio core
    core_service = CorePresidioService()
    
    # Ejemplos de texto para probar
    texts = [
        ("Juan Pérez tiene un correo electrónico: juan.perez@email.com", "es"),
        ("Mary Smith's phone number is +1 (555) 123-4567", "en")
    ]
    
    # Probar análisis de texto
    for text, lang in texts:
        print(f"\nAnalizando texto en {lang}: '{text}'")
        results = core_service.analyze_text(text, lang)
        print(f"Entidades detectadas: {len(results)}")
        for entity in results:
            print(f"  - {entity['entity_type']}: '{entity['text']}' (score: {entity['score']:.2f})")
    
    # Probar anonimización de texto
    for text, lang in texts:
        print(f"\nAnonimizando texto en {lang}: '{text}'")
        result = core_service.anonymize_text(text, lang)
        print(f"Texto anonimizado: '{result['text']}'")
        print(f"Entidades anonimizadas: {len(result['entities'])}")
        for entity in result['entities']:
            print(f"  - {entity['entity_type']}: '{entity['original_text']}' -> '{entity['replacement']}'")


def test_presidio_orchestrator():
    """Prueba el orquestador de Presidio."""
    print("\n=== PRUEBA DEL ORQUESTADOR DE PRESIDIO ===")
    
    # Crear instancia del orquestador
    orchestrator = PresidioOrchestrator()
    
    # Ejemplos de texto para probar
    texts = [
        ("Carlos Rodríguez vive en Bogotá, Colombia. Su cédula es 1234567890.", "es"),
        ("John Doe works at Microsoft in Seattle. His email is john@example.com", "en")
    ]
    
    # Probar análisis de texto
    for text, lang in texts:
        print(f"\nOrquestador - Analizando texto en {lang}")
        response = orchestrator.analyze_text(text, lang)
        print(f"Metadatos: {response['metadata']}")
        print(f"Entidades detectadas: {len(response['entities'])}")
        for entity in response['entities']:
            print(f"  - {entity['entity_type']}: '{entity['text']}' (score: {entity['score']:.2f})")
    
    # Probar anonimización de texto
    for text, lang in texts:
        print(f"\nOrquestador - Anonimizando texto en {lang}")
        response = orchestrator.anonymize_text(text, lang)
        print(f"Texto anonimizado: '{response['text']}'")
        print(f"Metadatos: {response['metadata']}")


if __name__ == "__main__":
    test_presidio_core()
    test_presidio_orchestrator()
