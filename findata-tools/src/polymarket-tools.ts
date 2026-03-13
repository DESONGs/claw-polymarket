/**
 * Polymarket tools - direct HTTP calls to Gamma API and CLOB API
 */

const GAMMA_BASE = "https://gamma-api.polymarket.com";
const CLOB_BASE = "https://clob.polymarket.com";
const TIMEOUT_MS = 30_000;

async function fetchWithTimeout(
  url: string,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), TIMEOUT_MS);
  if (signal) {
    signal.addEventListener("abort", () => ac.abort(), { once: true });
  }
  try {
    const resp = await fetch(url, { signal: ac.signal });
    clearTimeout(timer);
    const text = await resp.text();
    if (!resp.ok) {
      return { text: JSON.stringify({ error: `HTTP ${resp.status}`, body: text }), data: null };
    }
    let data: unknown = null;
    try { data = JSON.parse(text); } catch { /* raw text */ }
    return { text, data };
  } catch (err: any) {
    clearTimeout(timer);
    const msg = err?.name === "AbortError" ? "timeout" : (err?.message ?? String(err));
    return { text: JSON.stringify({ error: msg }), data: null };
  }
}

function formatMarketLine(m: any): string {
  let outcomes: string[];
  let prices: string[];
  try { outcomes = typeof m.outcomes === "string" ? JSON.parse(m.outcomes) : (m.outcomes ?? []); } catch { outcomes = []; }
  try { prices = typeof m.outcomePrices === "string" ? JSON.parse(m.outcomePrices) : (m.outcomePrices ?? []); } catch { prices = []; }
  const odds = outcomes.map((o: string, i: number) => {
    const pct = prices[i] ? (parseFloat(prices[i]) * 100).toFixed(1) + "%" : "N/A";
    return `${o}: ${pct}`;
  }).join(", ");
  const vol = m.volume24hr ? ` | 24h vol: $${Number(m.volume24hr).toLocaleString("en-US", { maximumFractionDigits: 0 })}` : "";
  return `- ${m.question}  →  ${odds}${vol}`;
}

async function searchMarkets(
  query: string,
  limit: number,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const aliases: Record<string, string> = {
    "比特币": "bitcoin",
    "以太坊": "ethereum",
    "原油": "crude oil",
    "油价": "oil price",
    "黄金": "gold",
    "伊朗": "iran",
    "美国": "us",
    "中国": "china",
    "俄乌": "russia ukraine",
  };

  const searchQueries: string[] = [];
  const trimmed = query.trim();
  if (trimmed) searchQueries.push(trimmed);
  let translated = trimmed;
  for (const [zh, en] of Object.entries(aliases)) {
    translated = translated.replaceAll(zh, en);
  }
  if (translated && translated !== trimmed) {
    searchQueries.push(translated);
  }

  for (const q of searchQueries) {
    const url = `${GAMMA_BASE}/public-search?q=${encodeURIComponent(q)}&limit_per_type=${limit}`;
    const result = await fetchWithTimeout(url, signal);
    if (!result.data || typeof result.data !== "object") continue;
    const events: any[] = (result.data as any).events ?? [];
    const markets = events
      .flatMap((e: any) => e.markets ?? [])
      .filter((m: any) => !m.closed);
    const lines = markets.map(formatMarketLine);
    if (lines.length > 0) {
      const text = `Polymarket prediction markets for "${q}":\n${lines.join("\n")}`;
      return { text, data: markets };
    }
  }

  return { text: `No active markets found for "${query}"`, data: null };
}

async function getMarket(
  idOrSlug: string,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const isNumeric = /^\d+$/.test(idOrSlug);
  const url = isNumeric
    ? `${GAMMA_BASE}/markets/${idOrSlug}`
    : `${GAMMA_BASE}/markets?slug=${encodeURIComponent(idOrSlug)}`;
  return fetchWithTimeout(url, signal);
}

async function getMidpoint(
  tokenId: string,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const url = `${CLOB_BASE}/midpoint?token_id=${encodeURIComponent(tokenId)}`;
  return fetchWithTimeout(url, signal);
}

async function getSpread(
  tokenId: string,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  return fetchWithTimeout(
    `${CLOB_BASE}/spread?token_id=${encodeURIComponent(tokenId)}`,
    signal,
  );
}

async function getPriceHistory(
  tokenId: string,
  interval: string,
  fidelity: number,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const params = new URLSearchParams({
    market: tokenId,
    interval,
    fidelity: String(fidelity),
  });
  return fetchWithTimeout(`${CLOB_BASE}/prices-history?${params}`, signal);
}

async function getBook(
  tokenId: string,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  return fetchWithTimeout(
    `${CLOB_BASE}/book?token_id=${encodeURIComponent(tokenId)}`,
    signal,
  );
}

export function createPolymarketTools() {
  return [
    {
      name: "polymarket_search",
      label: "Polymarket Search",
      description:
        "Search Polymarket prediction markets by keyword. Returns markets with titles, current probabilities, and volume. Works for any topic: politics, crypto, sports, geopolitics, etc.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search keywords (e.g. 'crude oil', 'bitcoin price', 'election')" },
          limit: { type: "number", description: "Max results, default 5" },
        },
        required: ["query"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await searchMarkets(
          String(params.query),
          Number(params.limit ?? 5),
          signal,
        );
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "polymarket_market_detail",
      label: "Polymarket Market Detail",
      description: "Get detailed info for a specific Polymarket prediction market including current odds, volume, and resolution criteria.",
      parameters: {
        type: "object",
        properties: {
          id_or_slug: { type: "string", description: "Market ID or slug" },
        },
        required: ["id_or_slug"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await getMarket(
          String(params.id_or_slug),
          signal,
        );
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "polymarket_midpoint",
      label: "Polymarket Midpoint",
      description: "Get the current implied probability (midpoint price) for a Polymarket token.",
      parameters: {
        type: "object",
        properties: {
          token_id: { type: "string", description: "Token ID (numeric or 0x hex)" },
        },
        required: ["token_id"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await getMidpoint(
          String(params.token_id),
          signal,
        );
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "polymarket_spread",
      label: "Polymarket Spread",
      description:
        "Get bid/ask spread for a Polymarket token. A narrow spread indicates high market maker confidence; a wide spread suggests uncertainty or low liquidity.",
      parameters: {
        type: "object",
        properties: {
          token_id: { type: "string", description: "Token ID (numeric or 0x hex)" },
        },
        required: ["token_id"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await getSpread(
          String(params.token_id),
          signal,
        );
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "polymarket_price_history",
      label: "Polymarket Price History",
      description:
        "Get probability price history for a Polymarket token over time. Use to identify trends, momentum, and rate of change in crowd consensus.",
      parameters: {
        type: "object",
        properties: {
          token_id: { type: "string", description: "Token ID (numeric or 0x hex)" },
          interval: {
            type: "string",
            enum: ["max", "1w", "1d", "6h", "1h"],
            description: "Time range. Default: max",
          },
          fidelity: {
            type: "number",
            description: "Minutes per data point. Default: 60",
          },
        },
        required: ["token_id"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await getPriceHistory(
          String(params.token_id),
          String(params.interval ?? "max"),
          Number(params.fidelity ?? 60),
          signal,
        );
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "polymarket_book",
      label: "Polymarket Order Book",
      description:
        "Get order book (bids and asks) for a Polymarket token. Use to gauge directional pressure — bid-heavy books suggest bullish sentiment, ask-heavy suggests bearish.",
      parameters: {
        type: "object",
        properties: {
          token_id: { type: "string", description: "Token ID (numeric or 0x hex)" },
        },
        required: ["token_id"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await getBook(
          String(params.token_id),
          signal,
        );
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
  ];
}
