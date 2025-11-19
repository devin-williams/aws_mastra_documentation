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
