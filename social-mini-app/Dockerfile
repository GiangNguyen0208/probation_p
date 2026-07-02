FROM node:20-alpine AS builder
WORKDIR /app
COPY social-mini-app/package.json social-mini-app/yarn.lock ./
RUN corepack enable && yarn install --immutable
COPY social-mini-app/ ./
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN yarn build

