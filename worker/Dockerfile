FROM node:20-slim
WORKDIR /app
COPY package.json .
RUN npm install
COPY queue.js .
CMD ["node", "queue.js"]
