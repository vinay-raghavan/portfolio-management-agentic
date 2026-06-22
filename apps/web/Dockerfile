FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci

FROM deps AS build
ARG VITE_AGENT_API_URL=http://localhost:8000
ENV VITE_AGENT_API_URL=$VITE_AGENT_API_URL
COPY apps/web ./
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY apps/web/package*.json ./
EXPOSE 3000
CMD ["npm", "run", "preview"]
