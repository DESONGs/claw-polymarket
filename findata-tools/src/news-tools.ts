/**
 * OpenNews API tools - calls 6551.io REST API via native fetch
 */
const BASE_URL = "https://ai.6551.io";

export function createNewsTools(token: string) {
  return [
    {
      name: "news_search",
      label: "Crypto News Search",
      description:
        "Search crypto news with AI ratings and trading signals. Returns articles with AI score (0-100), signal (long/short/neutral), and summary. Use for market overview, coin-specific news, or high-impact events.",
      parameters: {
        type: "object",
        properties: {
          q: { type: "string", description: "Full-text keyword search (e.g. 'bitcoin ETF', 'crude oil')" },
          coins: {
            type: "array",
            items: { type: "string" },
            description: "Filter by coin symbols e.g. ['BTC','ETH']",
          },
          hasCoin: { type: "boolean", description: "Only return news with associated coins" },
          limit: { type: "number", description: "Max results 1-100, default 10" },
          page: { type: "number", description: "Page number 1-based, default 1" },
        },
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const body: Record<string, unknown> = {
          limit: params.limit ?? 10,
          page: params.page ?? 1,
        };
        if (params.q) body.q = params.q;
        if (params.coins) body.coins = params.coins;
        if (params.hasCoin !== undefined) body.hasCoin = params.hasCoin;

        const resp = await fetch(`${BASE_URL}/open/news_search`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
          signal,
        });
        const text = await resp.text();
        let data: unknown = null;
        try { data = JSON.parse(text); } catch { /* raw text */ }
        if (!resp.ok) {
          return {
            content: [{ type: "text" as const, text: JSON.stringify({ error: `HTTP ${resp.status}`, body: text }) }],
            details: null,
          };
        }
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "news_sources",
      label: "Crypto News Sources",
      description: "List all available crypto news source categories (news, listing, onchain, meme, market).",
      parameters: {
        type: "object",
        properties: {},
      },
      async execute(
        _toolCallId: string,
        _params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const resp = await fetch(`${BASE_URL}/open/news_type`, {
          headers: { "Authorization": `Bearer ${token}` },
          signal,
        });
        const text = await resp.text();
        let data: unknown = null;
        try { data = JSON.parse(text); } catch { /* raw */ }
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
  ];
}
