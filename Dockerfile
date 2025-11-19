# Use official Node.js LTS image
FROM node:20-slim

# Set working directory
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm@10.15.0

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the Mastra application
RUN pnpm run build

# Expose the port
EXPOSE 4111

# Set environment to production
ENV NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:4111/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Start the server using the built output
CMD ["node", "--import=./.mastra/output/instrumentation.mjs", ".mastra/output/index.mjs"]
