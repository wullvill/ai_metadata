# ============================================================
# Frontend — Multi-stage build
# Stage 1: Build with Node.js
# Stage 2: Serve with nginx
# ============================================================

# ---- Build Stage ----
FROM node:20.20.1  AS build

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


# ---- Runtime Stage ----
FROM nginx:1.30.3-alpine

# 复制自定义 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从 build 阶段复制构建产物
COPY --from=build /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1
