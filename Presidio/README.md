# Presidio - Flujo del Programa

## Arquitectura General

El sistema de Presidio para la detección y anonimización de información sensible sigue un flujo de procesamiento estructurado en múltiples capas:

```mermaid
[Cliente] → [API (Flask)] → [Controlador] → [Orquestador] → [Servicios] → [Reconocedores]
```

## Flujo de Ejecución

1. **Inicio de la Aplicación** (`main.py`):
   - Se carga el servicio Flair (si es posible)
   - Se inicializa el servicio unificado de Presidio
   - Se inicializa el procesador de archivos
   - Se crea el servicio orquestador
   - Se inicializa el controlador con las rutas API
   - Se lanza el servidor Flask

2. **Recepción de Solicitudes** (`presidio_controller.py`):
   - El controlador recibe la solicitud HTTP
   - Extrae los parámetros (texto, idioma, tipos de entidades)
   - Valida la entrada básica
   - Envía la solicitud al orquestador

3. **Orquestación** (`presidio_orchestrator_service.py`):
   - Valida parámetros avanzados
   - Determina qué servicios utilizar
   - Registra eventos y métricas
   - Coordina el flujo entre servicios

4. **Procesamiento Principal** (`unified_presidio_service.py`):
   - Si es un archivo: extrae texto con `file_processor.py`
   - Inicializa los motores NLP adecuados según el idioma
   - Configura los reconocedores personalizados y estándar
   - Realiza la detección de entidades
   - Si Flair está disponible: valida entidades con contexto adicional
   - Para anonimización: reemplaza las entidades detectadas

5. **Reconocimiento de Entidades**:
   - Los reconocedores estándar de Presidio detectan entidades comunes
   - Los reconocedores personalizados (email, teléfono, documentos colombianos) aplican reglas específicas
   - El validador Flair (`flair_validator.py`) proporciona validación contextual adicional

6. **Retorno de Resultados**:
   - El servicio unificado devuelve los resultados al orquestador
   - El orquestador formatea y enriquece la respuesta
   - El controlador convierte los datos a formato JSON
   - La API devuelve la respuesta al cliente

## Flujo de Análisis de Texto

```mermaid
[Texto] → [Análisis NLP] → [Detección de Entidades] → [Validación con Flair] → [Resultados]
```

## Flujo de Anonimización

```mermaid
[Texto] → [Análisis NLP] → [Detección de Entidades] → [Validación] → [Reemplazo de Entidades] → [Texto Anonimizado]
```

## Flujo de Procesamiento de Archivos

```mermaid
[Archivo] → [Extracción de Texto] → [Análisis NLP] → [Detección de Entidades] → [Validación] → [Resultados/Anonimización] → [Archivo Procesado]
```

Este flujo modular permite una alta flexibilidad, habilitando el procesamiento de diversos formatos de entrada, múltiples idiomas, y diferentes tipos de entidades sensibles con un enfoque en la precisión y el rendimiento.
