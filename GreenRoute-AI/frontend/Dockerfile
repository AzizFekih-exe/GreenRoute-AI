FROM node:18-alpine

WORKDIR /app

# Copy package descriptors from context
COPY frontend/package.json ./

# Install npm packages
RUN npm install

# Copy frontend source files
COPY frontend/ ./

EXPOSE 8501

CMD ["npm", "run", "dev"]
