/**
 * OpenBB tools - calls local OpenBB API server at 127.0.0.1:6900
 */
const OPENBB_BASE = "http://127.0.0.1:6900/api/v1";
const TIMEOUT_MS = 30_000;

async function openbbFetch(
  path: string,
  params: Record<string, string>,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), TIMEOUT_MS);
  if (signal) {
    signal.addEventListener("abort", () => ac.abort(), { once: true });
  }
  const qs = new URLSearchParams(params).toString();
  const url = `${OPENBB_BASE}${path}${qs ? "?" + qs : ""}`;
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

export function createOpenBBTools() {
  return [
    {
      name: "openbb_stock",
      label: "Stock Data",
      description:
        "Get stock/ETF/futures/crypto price data. Use mode='quote' for real-time price, mode='history' for historical OHLCV candlestick data. Supports tickers like AAPL, TSLA, BTC-USD, CL=F (crude oil), GC=F (gold).",
      parameters: {
        type: "object",
        properties: {
          symbol: { type: "string", description: "Ticker symbol (e.g. AAPL, TSLA, CL=F, GC=F, BTC-USD)" },
          mode: { type: "string", enum: ["quote", "history"], description: "quote = real-time price; history = historical OHLCV. Default: quote" },
          interval: { type: "string", enum: ["1d", "1wk", "1mo"], description: "Candle interval for history mode. Default: 1d" },
          start_date: { type: "string", description: "Start date YYYY-MM-DD (history mode)" },
          end_date: { type: "string", description: "End date YYYY-MM-DD (history mode, default today)" },
          provider: { type: "string", description: "Data provider, default yfinance" },
        },
        required: ["symbol"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const mode = String(params.mode ?? "quote");
        const provider = String(params.provider ?? "yfinance");

        if (mode === "history") {
          const p: Record<string, string> = {
            symbol: String(params.symbol),
            provider,
            interval: String(params.interval ?? "1d"),
          };
          if (params.start_date) p.start_date = String(params.start_date);
          if (params.end_date) p.end_date = String(params.end_date);
          const { text, data } = await openbbFetch("/equity/price/historical", p, signal);
          return { content: [{ type: "text" as const, text }], details: data };
        }

        // default: quote
        const p: Record<string, string> = {
          symbol: String(params.symbol),
          provider,
        };
        const { text, data } = await openbbFetch("/equity/price/quote", p, signal);
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "openbb_company_info",
      label: "Company Profile",
      description:
        "Get company fundamentals: sector, industry, description, employees, market cap, website.",
      parameters: {
        type: "object",
        properties: {
          symbol: { type: "string", description: "Stock ticker (e.g. AAPL, MSFT)" },
          provider: { type: "string", description: "Data provider, default yfinance" },
        },
        required: ["symbol"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const p: Record<string, string> = {
          symbol: String(params.symbol),
          provider: String(params.provider ?? "yfinance"),
        };
        const { text, data } = await openbbFetch("/equity/fundamentals/profile", p, signal);
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "openbb_economy",
      label: "Economic Data",
      description:
        "Get macroeconomic data. Use type='calendar' for upcoming economic events (CPI, FOMC, jobs report); type='gdp' for GDP figures by country; type='cpi' for inflation data.",
      parameters: {
        type: "object",
        properties: {
          type: { type: "string", enum: ["calendar", "gdp", "cpi"], description: "Data type. Default: calendar" },
          start_date: { type: "string", description: "Start date YYYY-MM-DD (calendar mode)" },
          end_date: { type: "string", description: "End date YYYY-MM-DD (calendar mode)" },
          country: { type: "string", description: "Country name for gdp/cpi (e.g. united_states, china, japan)" },
          provider: { type: "string", description: "Data provider. calendar=nasdaq, gdp/cpi=oecd" },
        },
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const dataType = String(params.type ?? "calendar");

        if (dataType === "gdp") {
          const p: Record<string, string> = { provider: String(params.provider ?? "oecd") };
          if (params.country) p.country = String(params.country);
          const { text, data } = await openbbFetch("/economy/gdp/real", p, signal);
          return { content: [{ type: "text" as const, text }], details: data };
        }

        if (dataType === "cpi") {
          const p: Record<string, string> = { provider: String(params.provider ?? "oecd") };
          if (params.country) p.country = String(params.country);
          const { text, data } = await openbbFetch("/economy/cpi", p, signal);
          return { content: [{ type: "text" as const, text }], details: data };
        }

        // default: calendar
        const p: Record<string, string> = { provider: String(params.provider ?? "nasdaq") };
        if (params.start_date) p.start_date = String(params.start_date);
        if (params.end_date) p.end_date = String(params.end_date);
        const { text, data } = await openbbFetch("/economy/calendar", p, signal);
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
  ];
}
