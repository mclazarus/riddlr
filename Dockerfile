FROM python:3.10

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY riddlr.py .

RUN mkdir -p /app/data

CMD ["python", "riddlr.py"]
