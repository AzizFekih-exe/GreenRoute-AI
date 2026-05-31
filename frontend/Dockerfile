FROM node:18-alpine

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .

EXPOSE 8501

CMD ["npm", "run", "dev", "--", "--port", "8501", "--host", "0.0.0.0"]
