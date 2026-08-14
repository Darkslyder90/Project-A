# Produktiv-Image: baut den React-Build und liefert ihn statisch per nginx aus
# (siehe Briefing: "Frontend (gebauter React-Build, statisch ausgeliefert)").
# API-Aufrufe (/api/*, /health) werden NICHT hier, sondern vom vorgelagerten
# Reverse Proxy (Caddy, siehe Caddyfile im Repo-Root) direkt an den
# Backend-Container weitergeleitet - dieses Image kennt das Backend gar nicht.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
