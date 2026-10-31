# Build dari akar proyek: docker build -f deploy/web.Dockerfile .
FROM node:26-slim AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Image akhir hanya berisi Nginx dan file statis, tanpa Node.js.
FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/keamanan.conf /etc/nginx/keamanan.conf
COPY --from=build /src/out /usr/share/nginx/html
EXPOSE 8443
