FROM arm64v8/golang:alpine as build-env

ARG APP_VERSION

RUN apk add --no-cache git

RUN export GO111MODULE=on && export CGO_ENABLED=0 \
    && go get -d "github.com/hashicorp/vault-k8s@v${APP_VERSION}" \
    # Build Vault k8s from source
    && cd "/go/pkg/mod/github.com/hashicorp/vault-k8s@v${APP_VERSION}" \
    && go build -o /go/bin/main .

FROM scratch

COPY --from=build-env /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build-env /go/bin/main /

ENTRYPOINT ["/main"]
