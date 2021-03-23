FROM ubuntu:20.10

ARG VERSION="1.0.0"

RUN apt update && apt install -y zipalign

ENTRYPOINT ["zipalign"]