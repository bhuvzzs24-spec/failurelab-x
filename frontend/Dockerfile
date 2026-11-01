FROM node:24-alpine AS dependencies
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY frontend/ .
# Contract validation remains typechecked in Docker; its shared spec is outside frontend.
COPY docs/openapi.json /docs/openapi.json
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN addgroup -S -g 10001 lab && adduser -S -u 10001 -G lab lab
COPY --from=build --chown=lab:lab /app/.next/standalone ./
COPY --from=build --chown=lab:lab /app/.next/static ./.next/static
USER 10001
EXPOSE 3000
CMD ["node", "server.js"]
