# Build stage
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage — nginx serves the built static files
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# nginx config: proxy /api and /ws to the backend, serve everything else as SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
