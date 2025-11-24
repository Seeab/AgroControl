# Usamos una imagen ligera de Python
FROM python:3.10-slim

# Evita que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# 1. Instalar dependencias del SISTEMA para WeasyPrint y Postgres
# Esto es lo que te salva de errores al generar PDFs
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 3. Copiar el proyecto
COPY . .

# 4. Recolectar archivos estáticos
RUN python manage.py collectstatic --noinput

# 5. Comando para iniciar Gunicorn
# Asegúrate de que 'AgroControl' coincida con el nombre de la carpeta donde está wsgi.py
CMD ["gunicorn", "AgroControl.wsgi:application", "--bind", "0.0.0.0:8000"]