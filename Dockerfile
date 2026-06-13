FROM python:3.12-slim
LABEL org.opencontainers.image.source=https://github.com/aldi-f/mayo

COPY requirements.txt .

RUN python3 -m pip install  -r requirements.txt --user

COPY ./app ./app

WORKDIR /app

CMD ["python3","-m", "app"]
