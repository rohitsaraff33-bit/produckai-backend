FROM node:20-alpine

WORKDIR /app/apps/web

# Copy package files
COPY apps/web/package*.json ./

# Install dependencies
RUN npm install

# Copy app files
COPY apps/web .

# Expose port
EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev"]
