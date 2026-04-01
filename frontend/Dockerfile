FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app

ARG VITE_API_BASE
ARG VITE_BASIC_AUTH
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_BASIC_AUTH=${VITE_BASIC_AUTH}

RUN npm run build

EXPOSE 4173

CMD ["npm", "run", "preview"]
