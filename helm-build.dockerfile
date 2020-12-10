FROM ubuntu:20.10

RUN apt update && apt install -y curl apt-transport-https gnupg

RUN curl https://baltocdn.com/helm/signing.asc | apt-key add - && echo "deb https://baltocdn.com/helm/stable/debian/ all main" | tee /etc/apt/sources.list.d/helm-stable-debian.list

RUN apt update && apt-get install helm

ENTRYPOINT ["helm"]