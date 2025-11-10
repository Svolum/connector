FROM node:18-slim

WORKDIR /app

COPY ./web/package.json ./
RUN npm install

COPY ./web/server.js ./web/index.html ./web/scripts.js ./

RUN mkdir -p images

EXPOSE 3000

CMD ["node", "server.js"]