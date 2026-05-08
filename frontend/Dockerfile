# frontend/Dockerfile
FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

# ── dev ──────────────────────────────────────────────────────────────────────
FROM base AS dev

RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── prod ─────────────────────────────────────────────────────────────────────
FROM base AS prod-builder

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine AS prod
COPY --from=prod-builder /app/dist /srv
COPY Caddyfile.spa /etc/caddy/Caddyfile
EXPOSE 80
