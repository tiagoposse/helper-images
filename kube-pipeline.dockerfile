FROM alpine:3.12.0

ARG VERSION="1.0.0"
ARG KUBECTL_VERSION="v1.18.10"
ARG ARCH="amd64"

RUN wget https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/$ARCH/kubectl \
    && chmod +x ./kubectl && mv ./kubectl /usr/local/bin/kubectl

ENTRYPOINT [ "kubectl" ]