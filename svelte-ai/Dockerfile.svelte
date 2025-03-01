# Use Node.js 22 (latest) with Alpine for a smaller image
FROM node:22-alpine

# Install pnpm globally using npm (since it’s not bundled by default)
RUN npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy only the dependency-related files first to leverage Docker caching
COPY package.json pnpm-lock.yaml ./

# Copy the rest of the application files
COPY . .

# Install dependencies with pnpm
RUN pnpm install --frozen-lockfile

# Build the Svelte app (uncomment if you need a production build)
# RUN pnpm run build

# Expose port 8080 for the app
EXPOSE 8080

# Start the development server (assumes 'dev' script uses Vite or similar)
CMD ["npm", "run", "dev", "--host", "0.0.0.0"]