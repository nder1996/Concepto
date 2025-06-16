# Tests del Proyecto Presidio API

Esta carpeta contiene pruebas para validar el funcionamiento de los diferentes componentes de la API de Presidio.

## Estructura

- `test_recognizers.py`: Pruebas para los reconocedores personalizados
  - EmailRecognizer
  - PhoneRecognizer
  - ColombianIDRecognizer

## Ejecución de pruebas

Para ejecutar las pruebas, desde el directorio raíz del proyecto:

```bash
# Ejecutar todas las pruebas
python -m unittest discover tests

# O ejecutar un archivo específico
python tests/test_recognizers.py
```
