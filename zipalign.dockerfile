FROM ubuntu:20.10

RUN apt update && apt install -y zipalign

ENTRYPOINT ["zipalign"]