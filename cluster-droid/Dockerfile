FROM arm64v8/python:3.9-alpine

ARG ARCH=arm64
ARG HELM_VERSION
ARG KUBECTL_VERSION
ARG YQ_VERSION=3.4.1

ENV PLUGIN_SERVER=127.0.0.1
ENV PLUGIN_SERVER_PORT=6443
ENV PLUGIN_DEFAULT_TOKEN_PATH=/var/run/secrets/kubernetes.io/serviceaccount/token
ENV PLUGIN_DEFAULT_CA_PATH=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
ENV VAULT_ADDR=vault-internal.vault.svc:8200
ENV VAULT_CACERT=/

RUN apk update && apk add curl vim openssl

RUN curl -LO https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_${ARCH} && mv yq_linux_${ARCH} /usr/bin/yq && chmod +x /usr/bin/yq

RUN curl -LO https://get.helm.sh/helm-v${HELM_VERSION}-linux-${ARCH}.tar.gz && \
    tar -xzvf helm-v${HELM_VERSION}-linux-${ARCH}.tar.gz && rm helm-v$HELM_VERSION-linux-${ARCH}.tar.gz && \ 
    chmod +x linux-${ARCH}/helm && mv linux-${ARCH}/helm /usr/local/bin/helm && rm -rf linux-${ARCH}

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" && \
    chmod +x ./kubectl && mv ./kubectl /usr/local/bin/kubectl

COPY requirements.txt main.py /app/

RUN pip install -r /app/requirements.txt

ENTRYPOINT [ "python", "/app/main.py" ]