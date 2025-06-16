FROM python:3.9-slim

# Instalamos dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc g++ tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*

# Actualizamos pip y establecemos configuraciones para evitar problemas
RUN pip install --upgrade pip setuptools wheel

# Copiamos primero solo los requerimientos para aprovechar la caché de Docker
COPY requerimientos.txt .

# Instalamos las dependencias python
RUN pip install --no-cache-dir -r requerimientos.txt

# Instalamos spaCy y los modelos básicos para inglés y español
RUN pip install --no-cache-dir spacy==3.5.3
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download es_core_news_sm

COPY . /app/
WORKDIR /app
EXPOSE 5000
# Añadir variable de entorno para indicar que estamos en Docker
ENV RUNNING_IN_DOCKER=True
# Configurar Python para no almacenar en buffer la salida
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]