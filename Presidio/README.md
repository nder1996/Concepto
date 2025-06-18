# Presidio API

Servicio para detección y anonimización de información personal (PII) utilizando Microsoft Presidio, con soporte para español e inglés.

## Requisitos

- Python 3.8 o superior
- Docker (opcional para despliegue en contenedores)

## Instalación

### Instalación local

1. Clonar el repositorio:
```
git clone <url-repositorio>
cd Presidio
```

2. Instalar dependencias:
```
pip install -r requerimientos.txt
```

3. Instalar modelos de lenguaje para spaCy:
```
python src/config/setup.py
```

### Usando Docker

1. Construir la imagen:
```
docker build -t presidio-api .
```

2. Ejecutar el contenedor:
```
docker run -p 5000:5000 presidio-api
```

## Uso

### Detección de entidades

```
POST /analyze
Content-Type: application/json

{
    "text": "Mi nombre es Juan Pérez y mi correo es juan.perez@example.com",
    "language": "es"
}
```

### Anonimización de entidades

```
POST /anonymize
Content-Type: application/json

{
    "text": "Mi nombre es Juan Pérez y mi correo es juan.perez@example.com",
    "language": "es"
}
```

### Análisis de archivos

```
POST /analyze-file
Content-Type: multipart/form-data
form-data:
    - file: [archivo]
    - language: "es"
```

## Idiomas soportados

- Español (es)
- Inglés (en)

## Entidades detectadas

- PERSON: Nombres de personas
- PHONE_NUMBER: Números telefónicos
- EMAIL_ADDRESS: Direcciones de correo electrónico
- Otras entidades personalizadas

## Solución de problemas

### Si el texto en español no se analiza correctamente:

1. Verifica que se hayan instalado los modelos de lenguaje correctamente:
```
python -c "import spacy; print(spacy.util.is_package('es_core_news_md'))"
```

2. Si la respuesta es False, ejecuta nuevamente `python src/config/setup.py`

3. Asegúrate de especificar el parámetro `language: "es"` en las peticiones

### Si el texto en inglés funciona pero el español no:

El modelo de lenguaje para español puede no estar cargándose correctamente. Verifica los logs de la aplicación para más detalles.
