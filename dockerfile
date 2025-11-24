# Usamos Python 3.11 slim como querías
FROM python:3.11-slim

# Variables de entorno para optimizar Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# 1. Instalar dependencias del SISTEMA para WeasyPrint y Postgres
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

# 4. Recolectar estáticos
RUN python manage.py collectstatic --noinput

# 5. Comando de inicio (MODIFICADO PARA EVITAR ERROR 128)
# Usamos "sh -c" para asegurar que el sistema encuentre gunicorn correctamente
CMD ["sh", "-c", "gunicorn AgroControl.wsgi:application --bind 0.0.0.0:8000"]