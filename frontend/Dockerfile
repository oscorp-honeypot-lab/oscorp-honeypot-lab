FROM node:24.14.0-alpine@sha256:e9445c64ace1a9b5cdc60fc98dd82d1e5142985d902f41c2407e8fffe49d46a3

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci \
    && mkdir -p /app/node_modules/.vite /app/node_modules/.cache \
    && chown -R node:node /app/node_modules/.vite /app/node_modules/.cache

COPY --chown=node:node frontend/ ./
RUN chown node:node /app

USER node

EXPOSE 5173

CMD ["npm", "run", "dev"]
