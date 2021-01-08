ARG VAULT_VERSION
ARG YQ_VERSION=4.4.0

FROM vault:${VAULT_VERSION} as vault

FROM mikefarah/yq:${YQ_VERSION} as yq

FROM arm64v8/python:3.9-alpine

COPY --from=vault /bin/vault /usr/local/bin
COPY --from=yq /usr/bin/yq /usr/local/bin

ARG ARCH=arm64
ARG HELM_VERSION
ARG KUBECTL_VERSION

ENV PYTHONBUFFERED=1

RUN apk update && apk add curl vim

RUN curl -LO https://get.helm.sh/helm-v${HELM_VERSION}-linux-${ARCH}.tar.gz && \
    tar -xzvf helm-v${HELM_VERSION}-linux-${ARCH}.tar.gz && rm helm-v$HELM_VERSION-linux-${ARCH}.tar.gz && \ 
    chmod +x linux-${ARCH}/helm && mv linux-${ARCH}/helm /usr/local/bin/helm && rm -rf linux-${ARCH}

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" && \
    chmod +x ./kubectl && mv ./kubectl /usr/local/bin/kubectl

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY /app/*.py /app/.appargs.yml /app/

ENTRYPOINT [ "python", "/app/main.py" ]