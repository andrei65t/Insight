# Development stage
FROM node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# Run with host 0.0.0.0 for Docker access
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
