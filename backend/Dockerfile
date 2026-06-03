# 1. Usamos una imagen oficial de Python liviana
FROM python:3.11-slim

# 2. Seteamos la carpeta de trabajo dentro del servidor
WORKDIR /code

# 3. Copiamos el archivo de requerimientos primero (ayuda a que buildee más rápido)
COPY ./requirements.txt /code/requirements.txt

# 4. Instalamos las dependencias
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 5. Copiamos todo el código de nuestra carpeta 'app' adentro del servidor
COPY ./app /code/app

# 6. Comando definitivo para arrancar FastAPI en producción
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]