ARG VERSION

FROM gcr.io/kaniko-project/executor:arm64-v${VERSION}

COPY --from=arm64v8/busybox:1.32.0 /bin /bin
# Declare /busybox as a volume to get it automatically in the path to ignore

ENV PATH /bin
