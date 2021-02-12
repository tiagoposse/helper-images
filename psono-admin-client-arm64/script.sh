#!/bin/sh

VERSION=$(cat VERSION)

git clone https://gitlab.com/psono/psono-admin-client.git /tmp/psono-admin-client

docker run -ti --rm -v /tmp/psono-admin-client:/app \
    node:10-slim sh -c "cd /app && npm config set registry https://psono.jfrog.io/psono/api/npm/npm/ && \
    npm config set @devexpress:registry https://psono.jfrog.io/psono/api/npm/npm/ && \
    npm config set @types:registry https://psono.jfrog.io/psono/api/npm/npm/ && \
    npm ci && \
    npm install -g karma-cli && \
    INLINE_RUNTIME_CHUNK=false npm run build"

cp VERSION build/VERSION.txt

docker buildx build -t registry.tiagoposse.com/psono-admin-client:$VERSION --push --platform=linux/arm64 /tmp/psono-admin-client

rm -rf /tmp/psono-admin-client