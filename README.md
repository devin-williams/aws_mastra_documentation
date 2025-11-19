# Deploying a Mastra Agent to Bedrock AgentCore

|    Information     |          Details          |
| :----------------: | :-----------------------: |
| Agentic Framework  |         Mastra AI         |
|     Components     | AgentCore Runtime, Docker |
| Example comlpexity |           Easy            |

## Prerequisites

- Node.js 20 or later
- pnpm 10.15 or later
- AWS CLI
- Docker
- python3 3.12 or later

## Setup Instructions

### 1. Install Mastra

```bash
mkdir my-agent && cd my-agent
```

```bash
pnpm init -y
pnpm add -D typescript @types/node mastra@latest
pnpm add @mastra/core@latest zod@^4
```

Add your `dev` and `build` scripts to your `package.json` file:

```json
"scripts": {
  "test": "echo \"Error: no test specified\" && exit 1",
  "dev": "mastra dev",
  "build": "mastra build"
}
```

Create and edit a `tsconfig.json` file:

```bash
touch tsconfig.json
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true,
    "outDir": "dist"
  },
  "include": ["src/**/*"]
}
```

In a `.env` file, add your API for the provider of your choice:

```bash
OPENAI_API_KEY=<your-api-key>
```

### 2. Create Agent

**Create a Tool**

We are going to create a tool for out agent first:

```bash
mkdir -p src/mastra/tools && touch src/mastra/tools/weather-tool.ts
```

```typescript
import { createTool } from "@mastra/core/tools";
import { z } from "zod";

export const weatherTool = createTool({
  id: "get-weather",
  description: "Get current weather for a location",
  inputSchema: z.object({
    location: z.string().describe("City name"),
  }),
  outputSchema: z.object({
    output: z.string(),
  }),
  execute: async () => {
    return {
      output: "The weather is sunny",
    };
  },
});
```

**Create an Agent**

Now that we have a tool for our agent, let's create the agent:

```bash
mkdir -p src/mastra/agents && touch src/mastra/agents/weather-agent.ts
```

```typescript
import { Agent } from "@mastra/core/agent";
import { weatherTool } from "../tools/weather-tool";

export const weatherAgent = new Agent({
  name: "Weather Agent",
  instructions: `
      You are a helpful weather assistant that provides accurate weather information.

      Your primary function is to help users get weather details for specific locations. When responding:
      - Always ask for a location if none is provided
      - If the location name isn't in English, please translate it
      - If giving a location with multiple parts (e.g. "New York, NY"), use the most relevant part (e.g. "New York")
      - Include relevant details like humidity, wind conditions, and precipitation
      - Keep responses concise but informative

      Use the weatherTool to fetch current weather data.
`,
  model: "openai/gpt-4.1",
  tools: { weatherTool },
});
```

### 3. Create the entrypoint for your agent

Create an `index.ts` file to be the entrypoint for our agent. We are going to add a custom route
that will allow AgentCore to communicate with our agent.

```bash
touch src/mastra/index.ts
```

```typescript
import { Mastra } from "@mastra/core/mastra";
import { weatherAgent } from "./agents/weather-agent";
import { registerApiRoute } from "@mastra/core/server";

export const mastra = new Mastra({
  agents: { weatherAgent },
  server: {
    apiRoutes: [
      registerApiRoute("/invocations", {
        method: "POST",
        handler: async (c) => {
          const mastra = c.get("mastra");
          const body = await c.req.json();

          const agent = mastra.getAgent("weatherAgent");

          const resp = await agent.generate([
            {
              role: "user",
              content: body.inputs || body.prompt || body.message,
            },
          ]);

          return c.json({ generated_text: resp.text });
        },
      }),
    ],
  },
});
```

AgentCore expects the `/invocations` endpoint as the base entrypoint for any agent.

### 4. Dockerize

Now we can create the Dockerfile that will containerize our agent:

```Dockerfile
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
```

And here is a `.dockerignore` that we can use as well:

```gitignore
# Dependencies
node_modules
.pnpm-store

# Build output (will be rebuilt in container)
.mastra
dist
```

### 5. Push to AWS ECR (Elastic Container Registry)

Set your variables:

```bash
export AWS_REGION=us-east-1
export REPO_NAME=mastra-agent
export IMAGE_TAG=latest
export AWS_ACCOUNT_ID=<your-aws-account-id>
```

**1. Create ECR Repository**

```bash
aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION
```

**2. Authenticate Docker with ECR**

```bash
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

**3. Tag Docker Image**

```bash
docker tag mastra-agent:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG
```

**4. Push to ECR**

```bash
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG
```

### 6. Push to AgentCore

We are going to use the `deploy-to-agentcore.py` script to create our agent runtime!

1. Create a virtual environment:
   ```bash
       python -m venv .venv
   ```
   And activate it with:
   ```bash
       source .venv/bin/activate
   ```
   Install the requirements:
   ```bash
       pip install -r requirements.txt
   ```
2. Run the script:
   ```bash
       python deploy-to-agentcore.py
   ```

### 7. Profit

Now head over to the `Agent Sandbox` under `Test` on the sidebar, select your agent, and test!

Input should be:

```json
{
  "inputs": "What is the weather like in San Francisco?"
}
```

Or alternatively:

```json
{
  "prompt": "What is the weather like in San Francisco?"
}
```

Or:

```json
{
  "message": "What is the weather like in San Francisco?"
}
```
