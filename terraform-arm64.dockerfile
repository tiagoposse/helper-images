FROM alpine

ARG ARCH="arm64"
ARG VERSION="0.14.6"

RUN wget https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_linux_${ARCH}.zip && \
    unzip terraform_${VERSION}_linux_${ARCH}.zip && mv terraform /usr/local/bin/

ENTRYPOINT [ "terraform" ]