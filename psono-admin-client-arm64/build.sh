npm config set registry https://psono.jfrog.io/psono/api/npm/npm/
npm config set @devexpress:registry https://psono.jfrog.io/psono/api/npm/npm/
npm config set @types:registry https://psono.jfrog.io/psono/api/npm/npm/
npm ci
npm install -g karma-cli
INLINE_RUNTIME_CHUNK=false npm run build