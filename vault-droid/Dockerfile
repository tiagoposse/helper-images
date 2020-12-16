FROM arm64v8/alpine

COPY app/ /app/
COPY requirements.txt /app/requirements.txt

RUN apk add py3-cryptography py3-pip && ln -s /usr/bin/python3 /usr/bin/python

RUN pip install -r /app/requirements.txt

WORKDIR /app

ENTRYPOINT [ "python", "/app/main.py" ]