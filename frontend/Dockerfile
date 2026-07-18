FROM node:20-alpine AS build
WORKDIR /app/frontend
COPY package.json yarn.lock* ./
RUN yarn install --frozen-lockfile || yarn install
COPY . .
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
RUN yarn build

FROM node:20-alpine
WORKDIR /app
RUN yarn global add serve
COPY --from=build /app/frontend/build ./build
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
