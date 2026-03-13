/**
 * geo_briefing - composite tool that fetches Twitter, News, Polymarket,
 * and OpenBB data in parallel and returns a structured briefing.
 */

const GAMMA_BASE = "https://gamma-api.polymarket.com";
const CLOB_BASE = "https://clob.polymarket.com";
const OPENBB_BASE = "http://127.0.0.1:6900/api/v1";
const TWITTER_BASE = "https://ai.6551.io";
const TIMEOUT_MS = 30_000;

async function fetchJson(
  url: string,
  opts?: { method?: string; headers?: Record<string, string>; body?: string },
): Promise<{ ok: boolean; data: any; error?: string }> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, { signal: ac.signal, ...opts });
    clearTimeout(timer);
    const text = await resp.text();
    if (!resp.ok) return { ok: false, data: null, error: `HTTP ${resp.status}: ${text.slice(0, 200)}` };
    try { return { ok: true, data: JSON.parse(text) }; } catch { return { ok: true, data: text }; }
  } catch (err: any) {
    clearTimeout(timer);
    return { ok: false, data: null, error: err?.name === "AbortError" ? "timeout" : (err?.message ?? String(err)) };
  }
}

// --- Twitter ---
async function fetchTwitter(keywords: string, token: string): Promise<string> {
  const res = await fetchJson(`${TWITTER_BASE}/open/twitter_search`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ keywords, product: "Top", maxResults: 5 }),
  });
  if (!res.ok) return `[Twitter error: ${res.error}]`;
  const tweets = res.data?.data?.tweets ?? res.data?.tweets ?? res.data?.data ?? [];
  if (!Array.isArray(tweets) || tweets.length === 0) return "[No tweets found]";
  return tweets.slice(0, 5).map((t: any) => {
    const likes = t.likeCount ?? t.favorite_count ?? 0;
    const rts = t.retweetCount ?? t.retweet_count ?? 0;
    const user = t.user?.name ?? t.author ?? "unknown";
    const text = (t.text ?? t.full_text ?? "").slice(0, 200);
    return `- @${user} (♥${likes} ↻${rts}): ${text}`;
  }).join("\n");
}

// --- News ---
async function fetchNews(keywords: string, token: string): Promise<string> {
  const res = await fetchJson(`${TWITTER_BASE}/open/news_search`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ q: keywords, limit: 5 }),
  });
  if (!res.ok) return `[News error: ${res.error}]`;
  const articles = res.data?.data ?? res.data?.articles ?? res.data ?? [];
  if (!Array.isArray(articles) || articles.length === 0) return "[No news found]";
  return articles.slice(0, 5).map((a: any) => {
    const score = a.aiScore != null ? ` [AI:${a.aiScore}]` : "";
    const signal = a.signal ? ` (${a.signal})` : "";
    return `- ${a.title ?? a.headline ?? "Untitled"}${score}${signal}\n  ${(a.summary ?? a.description ?? "").slice(0, 150)}`;
  }).join("\n");
}

// --- Polymarket ---
async function fetchPolymarkets(
  query: string,
  limit: number,
): Promise<string> {
  const res = await fetchJson(
    `${GAMMA_BASE}/public-search?q=${encodeURIComponent(query)}&limit_per_type=${limit}`,
  );
  if (!res.ok) return `[Polymarket search error: ${res.error}]`;

  const events: any[] = res.data?.events ?? [];
  const markets = events
    .flatMap((e: any) => e.markets ?? [])
    .filter((m: any) => !m.closed)
    .slice(0, limit);

  if (markets.length === 0) return "[No active prediction markets found]";

  const sections: string[] = [];
  for (const m of markets) {
    let outcomes: string[];
    let prices: string[];
    try { outcomes = typeof m.outcomes === "string" ? JSON.parse(m.outcomes) : (m.outcomes ?? []); } catch { outcomes = []; }
    try { prices = typeof m.outcomePrices === "string" ? JSON.parse(m.outcomePrices) : (m.outcomePrices ?? []); } catch { prices = []; }

    const odds = outcomes.map((o: string, i: number) => {
      const pct = prices[i] ? (parseFloat(prices[i]) * 100).toFixed(1) + "%" : "N/A";
      return `${o}: ${pct}`;
    }).join(", ");

    // Get first token for CLOB data
    const tokenId = m.clobTokenIds?.[0];
    let clobInfo = "";
    if (tokenId) {
      const [spreadRes, historyRes, bookRes] = await Promise.allSettled([
        fetchJson(`${CLOB_BASE}/spread?token_id=${encodeURIComponent(tokenId)}`),
        fetchJson(`${CLOB_BASE}/prices-history?${new URLSearchParams({ market: tokenId, interval: "1d", fidelity: "60" })}`),
        fetchJson(`${CLOB_BASE}/book?token_id=${encodeURIComponent(tokenId)}`),
      ]);

      // Spread
      if (spreadRes.status === "fulfilled" && spreadRes.value.ok) {
        const spread = spreadRes.value.data?.spread ?? spreadRes.value.data;
        clobInfo += `\n  Spread: ${typeof spread === "object" ? JSON.stringify(spread) : spread}`;
      }

      // Price history trend
      if (historyRes.status === "fulfilled" && historyRes.value.ok) {
        const history = historyRes.value.data?.history ?? historyRes.value.data;
        if (Array.isArray(history) && history.length >= 2) {
          const first = history[0]?.p ?? history[0]?.price;
          const last = history[history.length - 1]?.p ?? history[history.length - 1]?.price;
          if (first != null && last != null) {
            const delta = ((last - first) * 100).toFixed(1);
            clobInfo += `\n  24h trend: ${(first * 100).toFixed(1)}% → ${(last * 100).toFixed(1)}% (${Number(delta) >= 0 ? "+" : ""}${delta}%)`;
          }
        }
      }

      // Order book summary
      if (bookRes.status === "fulfilled" && bookRes.value.ok) {
        const book = bookRes.value.data;
        if (book?.bids && book?.asks) {
          const bidVol = (book.bids as any[]).reduce((s: number, b: any) => s + Number(b.size || 0), 0);
          const askVol = (book.asks as any[]).reduce((s: number, a: any) => s + Number(a.size || 0), 0);
          const pressure = bidVol > askVol * 1.2 ? "buy pressure" : askVol > bidVol * 1.2 ? "sell pressure" : "balanced";
          clobInfo += `\n  Order book: bids $${bidVol.toFixed(0)} vs asks $${askVol.toFixed(0)} (${pressure})`;
        }
      }
    }

    sections.push(`### ${m.question}\n  Odds: ${odds}${clobInfo}`);
  }

  return sections.join("\n\n");
}

// --- OpenBB Assets ---
async function fetchAssetQuotes(symbols: string[]): Promise<string> {
  if (symbols.length === 0) return "";
  const results = await Promise.allSettled(
    symbols.map((s) =>
      fetchJson(`${OPENBB_BASE}/equity/price/quote?symbol=${encodeURIComponent(s)}&provider=yfinance`),
    ),
  );
  const lines: string[] = [];
  for (let i = 0; i < symbols.length; i++) {
    const r = results[i];
    if (r.status !== "fulfilled" || !r.value.ok) {
      lines.push(`- ${symbols[i]}: [error]`);
      continue;
    }
    const d = Array.isArray(r.value.data?.results) ? r.value.data.results[0] : r.value.data;
    if (!d) { lines.push(`- ${symbols[i]}: [no data]`); continue; }
    const price = d.last_price ?? d.regular_market_price ?? d.close ?? "N/A";
    const change = d.change_percent ?? d.regular_market_change_percent;
    const chgStr = change != null ? ` (${Number(change) >= 0 ? "+" : ""}${Number(change).toFixed(2)}%)` : "";
    const name = d.name ?? d.short_name ?? symbols[i];
    lines.push(`- ${symbols[i]} (${name}): $${price}${chgStr}`);
  }
  return lines.join("\n");
}

// --- OpenBB Economy Calendar ---
async function fetchEconCalendar(): Promise<string> {
  const now = new Date();
  const end = new Date(now.getTime() + 7 * 86400_000);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  const res = await fetchJson(
    `${OPENBB_BASE}/economy/calendar?provider=nasdaq&start_date=${fmt(now)}&end_date=${fmt(end)}`,
  );
  if (!res.ok) return `[Calendar error: ${res.error}]`;
  const events = Array.isArray(res.data?.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
  if (events.length === 0) return "[No upcoming events]";
  return events.slice(0, 10).map((e: any) => {
    const date = e.date ?? e.event_date ?? "";
    const name = e.event ?? e.name ?? e.description ?? "Unknown";
    const country = e.country ? ` [${e.country}]` : "";
    return `- ${date}: ${name}${country}`;
  }).join("\n");
}

// --- Main ---
export function createGeoBriefingTool(twitterToken?: string, newsToken?: string) {
  return {
    name: "geo_briefing",
    label: "Geopolitical Briefing",
    description:
      "Composite intelligence briefing tool. Fetches Twitter sentiment, news coverage, Polymarket prediction odds (with spread/trend/order book), asset prices, and economic calendar in one call. Use for geopolitical event analysis.",
    parameters: {
      type: "object",
      properties: {
        event_keywords: {
          type: "string",
          description: "Event keywords for Twitter/News/Polymarket search (e.g. 'iran sanctions oil')",
        },
        polymarket_query: {
          type: "string",
          description: "Polymarket-specific search query. Defaults to event_keywords.",
        },
        asset_symbols: {
          type: "array",
          items: { type: "string" },
          description: 'Asset tickers to quote, e.g. ["CL=F","GC=F","BTC-USD"]',
        },
        market_limit: {
          type: "number",
          description: "Max Polymarket markets to analyze. Default: 3",
        },
      },
      required: ["event_keywords"],
    },
    async execute(
      _toolCallId: string,
      params: Record<string, unknown>,
      _signal?: AbortSignal,
    ) {
      const keywords = String(params.event_keywords);
      const pmQuery = String(params.polymarket_query ?? keywords);
      const symbols: string[] = Array.isArray(params.asset_symbols)
        ? params.asset_symbols.map(String)
        : [];
      const marketLimit = Number(params.market_limit ?? 3);

      const tasks: Array<Promise<string>> = [];
      const labels: string[] = [];

      // Twitter
      if (twitterToken) {
        labels.push("Twitter Sentiment");
        tasks.push(fetchTwitter(keywords, twitterToken));
      }

      // News
      if (newsToken) {
        labels.push("News Coverage");
        tasks.push(fetchNews(keywords, newsToken));
      }

      // Polymarket
      labels.push("Prediction Markets");
      tasks.push(fetchPolymarkets(pmQuery, marketLimit));

      // Asset prices
      if (symbols.length > 0) {
        labels.push("Asset Prices");
        tasks.push(fetchAssetQuotes(symbols));
      }

      // Economy calendar
      labels.push("Economic Calendar (Next 7 Days)");
      tasks.push(fetchEconCalendar());

      const results = await Promise.allSettled(tasks);

      const sections: string[] = [];
      for (let i = 0; i < labels.length; i++) {
        const r = results[i];
        const content = r.status === "fulfilled" ? r.value : `[error: ${(r as PromiseRejectedResult).reason}]`;
        if (content) {
          sections.push(`## ${labels[i]}\n${content}`);
        }
      }

      const briefing = sections.join("\n\n");
      return { content: [{ type: "text" as const, text: briefing }] };
    },
  };
}
