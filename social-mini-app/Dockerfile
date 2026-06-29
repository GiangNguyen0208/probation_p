FROM node:20-alpine AS builder
WORKDIR /app
COPY social-mini-app/package.json social-mini-app/package-lock.json ./
RUN npm ci
COPY social-mini-app/ ./
RUN npm run build

FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY social-mini-app/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
