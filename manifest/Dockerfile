FROM python:3.10-slim-buster
LABEL org.opencontainers.image.authors="zouwenxin126@126.com"

COPY * /app/
WORKDIR /app

RUN pip install pipenv && \
    pipenv sync

CMD ["pipenv", "run", "python", "/app/main.py"]
