FROM alpine

ARG ARCH="linux_arm64"
ARG VERSION="0.14.6"

RUN wget https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_${ARCH}.zip && \
    unzip terraform_${VERSION}_${ARCH}.zip && mv terraform /usr/local/bin/

ENTRYPOINT [ "terraform" ]