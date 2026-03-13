import { createTwitterTools } from "./src/twitter-tools.js";
import { createNewsTools } from "./src/news-tools.js";
import { createPolymarketTools } from "./src/polymarket-tools.js";
import { createOpenBBTools } from "./src/openbb-tools.js";
import { createGeoBriefingTool } from "./src/geo-briefing.js";

const findataPlugin = {
  id: "findata-tools",
  name: "Financial Data Tools",
  description: "Native tool functions for Twitter, crypto news, Polymarket, and OpenBB financial data",

  register(api: any) {
    const logger = api.logger;

    if (typeof api.registerTool !== "function") {
      logger.warn("[FinData] registerTool API not available");
      return;
    }

    // Twitter tools - require TWITTER_TOKEN
    const twitterToken = process.env.TWITTER_TOKEN;
    if (twitterToken) {
      const tools = createTwitterTools(twitterToken);
      for (const tool of tools) {
        api.registerTool(
          (ctx: any) => ctx.sandboxed ? null : tool,
          { name: tool.name, optional: true },
        );
      }
      logger.info(`[FinData] Registered ${tools.length} Twitter tools`);
    } else {
      logger.warn("[FinData] TWITTER_TOKEN not set - Twitter tools skipped");
    }

    // News tools - require OPENNEWS_TOKEN
    const newsToken = process.env.OPENNEWS_TOKEN;
    if (newsToken) {
      const tools = createNewsTools(newsToken);
      for (const tool of tools) {
        api.registerTool(
          (ctx: any) => ctx.sandboxed ? null : tool,
          { name: tool.name, optional: true },
        );
      }
      logger.info(`[FinData] Registered ${tools.length} News tools`);
    } else {
      logger.warn("[FinData] OPENNEWS_TOKEN not set - News tools skipped");
    }

    // Polymarket tools - require openclaw-polymarket-skill binary
    const pmTools = createPolymarketTools();
    for (const tool of pmTools) {
      api.registerTool(
        (ctx: any) => ctx.sandboxed ? null : tool,
        { name: tool.name, optional: true },
      );
    }
    logger.info(`[FinData] Registered ${pmTools.length} Polymarket tools`);

    // OpenBB tools - local API at 127.0.0.1:6900, no token needed
    const openbbTools = createOpenBBTools();
    for (const tool of openbbTools) {
      api.registerTool(
        (ctx: any) => ctx.sandboxed ? null : tool,
        { name: tool.name, optional: true },
      );
    }
    logger.info(`[FinData] Registered ${openbbTools.length} OpenBB tools`);

    // geo_briefing composite tool
    const geoBriefing = createGeoBriefingTool(twitterToken, newsToken);
    api.registerTool(
      (ctx: any) => ctx.sandboxed ? null : geoBriefing,
      { name: geoBriefing.name, optional: true },
    );
    logger.info(`[FinData] Registered geo_briefing composite tool`);
  },
};

export default findataPlugin;
