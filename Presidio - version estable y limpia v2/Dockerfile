FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc g++ tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
COPY requerimientos.txt .

# Instalamos NumPy con una versión específica para evitar problemas de compatibilidad
RUN pip install --no-cache-dir numpy==1.22.4

# Luego instalamos las demás dependencias
RUN pip install -r requerimientos.txt

# Instalamos spaCy y los modelos de idiomas para inglés y español
RUN pip install --no-cache-dir spacy==3.5.3
# Instalamos los modelos más completos para mejor reconocimiento de entidades
RUN python -m spacy download en_core_web_lg
RUN python -m spacy download es_core_news_md

# Forzamos la instalación de librería de países, estados y ciudades
#RUN pip install --no-cache-dir py-countries-states-cities-database>=1.2.1

COPY . /app/
WORKDIR /app
EXPOSE 5000
# Añadir variable de entorno para indicar que estamos en Docker
ENV RUNNING_IN_DOCKER=True
# Configurar Python para no almacenar en buffer la salida
ENV PYTHONUNBUFFERED=1

# Variable para definir el idioma por defecto (es=español, en=inglés)
ENV DEFAULT_LANGUAGE=es

# Configuración para permitir cambiar el idioma en tiempo de ejecución
ENV SUPPORTED_LANGUAGES=es,en

CMD ["python", "main.py"]