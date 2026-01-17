FROM python:3.13.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install grpcio grpcio-tools

COPY . .

EXPOSE 50051 

CMD ["python", "server.py"]
