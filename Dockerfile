FROM python:3.13-alpine

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir .

EXPOSE 8000


CMD ["litestar", "run", "--host", "0.0.0.0", "--port", "8000"]
