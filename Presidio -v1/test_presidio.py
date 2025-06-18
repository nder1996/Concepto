"""
Script de prueba para verificar la detección de entidades en diferentes idiomas.
Ejecutar con: python test_presidio.py
"""

import requests
import json
import sys

# URL del servicio (ajustar si es necesario)
BASE_URL = "http://localhost:5000"

def test_analyze(text, language):
    """
    Prueba el endpoint de análisis con un texto y lenguaje específicos
    """
    print(f"\n=== Probando análisis en {language} ===")
    print(f"Texto: {text}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"text": text, "language": language}
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"Entidades detectadas: {len(results)}")
            for entity in results:
                print(f"- {entity['entity_type']}: {text[entity['start']:entity['end']]} (Score: {entity['score']})")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error en la solicitud: {str(e)}")


def test_anonymize(text, language):
    """
    Prueba el endpoint de anonimización con un texto y lenguaje específicos
    """
    print(f"\n=== Probando anonimización en {language} ===")
    print(f"Texto original: {text}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/anonymize",
            json={"text": text, "language": language}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Texto anonimizado: {result['text']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error en la solicitud: {str(e)}")


def main():
    """
    Función principal que ejecuta las pruebas
    """
    # Texto de prueba en inglés
    english_text = """
    Dear Mr. Johnson, I am writing to confirm your appointment scheduled for March 15th, 2024.
    Your personal information on file includes: Full Name: Robert Michael Johnson, 
    Email: r.johnson@techcorp.com, Phone: (555) 123-4567, 
    Address: 123 Oak Street, Apartment 4B, New York, NY 10001, 
    Social Security Number: 123-45-6789, Date of Birth: January 15, 1985, 
    Credit Card: 4532-1234-5678-9012. Please bring your driver's license (NY-12345678) 
    and insurance card. If you need to reschedule, please call our office at (555) 987-6543 
    or email support@healthclinic.org. Thank you, Dr. Sarah Williams, Medical Director.
    """
    
    # Texto de prueba en español
    spanish_text = """
    Estimado Sr. Martínez, Le escribo para confirmar su cita programada para el 15 de marzo de 2024.
    Su información personal en archivo incluye: Nombre completo: Carlos Eduardo Martínez García, 
    Correo electrónico: c.martinez@empresatech.com, Teléfono: (34) 612-345-678, 
    Dirección: Calle Roble 123, Apartamento 4B, Madrid, España, 28001, 
    DNI: 12345678A, Fecha de nacimiento: 15 de enero de 1985, 
    Tarjeta de crédito: 4532-1234-5678-9012. Por favor traiga su carnet de conducir (B-12345678) 
    y tarjeta del seguro. Si necesita reprogramar, llame a nuestra oficina al (34) 987-654-321 
    o envíe un correo a citas@clinicasalud.org. Gracias, Dra. María González, Directora Médica.
    """
    
    # Probar análisis y anonimización en inglés
    test_analyze(english_text, "en")
    test_anonymize(english_text, "en")
    
    # Probar análisis y anonimización en español
    test_analyze(spanish_text, "es")
    test_anonymize(spanish_text, "es")


if __name__ == "__main__":
    main()
