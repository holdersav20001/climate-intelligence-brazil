# Stage 1: nothing to build yet
FROM node:20-alpine AS build
WORKDIR /app
COPY index.html .

# Stage 2: serve via nginx
FROM nginx:alpine
COPY --from=build /app/index.html /usr/share/nginx/html/index.html
EXPOSE 80
