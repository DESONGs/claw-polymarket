/**
 * Twitter API tools - calls 6551.io REST API via native fetch
 */
const BASE_URL = "https://ai.6551.io";

async function twitterApi(
  endpoint: string,
  body: Record<string, unknown>,
  token: string,
  signal?: AbortSignal,
): Promise<{ text: string; data: unknown }> {
  const resp = await fetch(`${BASE_URL}/open/${endpoint}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });
  const text = await resp.text();
  if (!resp.ok) {
    return { text: JSON.stringify({ error: `HTTP ${resp.status}`, body: text }), data: null };
  }
  let data: unknown = null;
  try { data = JSON.parse(text); } catch { /* raw text fallback */ }
  return { text, data };
}

export function createTwitterTools(token: string) {
  return [
    {
      name: "twitter_search",
      label: "Twitter Search",
      description:
        "Search tweets on Twitter/X. Returns tweets matching keywords, hashtags, or from specific users with engagement metrics.",
      parameters: {
        type: "object",
        properties: {
          keywords: { type: "string", description: "Search keywords" },
          fromUser: { type: "string", description: "Tweets from specific user (without @)" },
          hashtag: { type: "string", description: "Filter by hashtag (without #)" },
          minLikes: { type: "number", description: "Minimum likes threshold" },
          product: { type: "string", enum: ["Top", "Latest"], description: "Top (popular) or Latest (chronological)" },
          maxResults: { type: "number", description: "Max tweets 1-100, default 20" },
          sinceDate: { type: "string", description: "Start date YYYY-MM-DD" },
          untilDate: { type: "string", description: "End date YYYY-MM-DD" },
          lang: { type: "string", description: "Language code e.g. en, zh" },
        },
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const body: Record<string, unknown> = { maxResults: 20, product: "Top" };
        for (const key of ["keywords", "fromUser", "hashtag", "minLikes", "product", "sinceDate", "untilDate", "lang", "maxResults"]) {
          if (params[key] !== undefined && params[key] !== null) body[key] = params[key];
        }
        const { text, data } = await twitterApi("twitter_search", body, token, signal);
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "twitter_user_tweets",
      label: "Twitter User Tweets",
      description: "Get recent tweets from a specific Twitter/X user.",
      parameters: {
        type: "object",
        properties: {
          username: { type: "string", description: "Twitter username (without @)" },
          maxResults: { type: "number", description: "Max tweets 1-100, default 20" },
          product: { type: "string", enum: ["Top", "Latest"], description: "Sort order" },
        },
        required: ["username"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const body = {
          username: params.username,
          maxResults: params.maxResults ?? 20,
          product: params.product ?? "Latest",
        };
        const { text, data } = await twitterApi("twitter_user_tweets", body, token, signal);
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
    {
      name: "twitter_user_info",
      label: "Twitter User Info",
      description: "Get a Twitter/X user profile (followers, bio, verified status).",
      parameters: {
        type: "object",
        properties: {
          username: { type: "string", description: "Twitter username (without @)" },
        },
        required: ["username"],
      },
      async execute(
        _toolCallId: string,
        params: Record<string, unknown>,
        signal?: AbortSignal,
      ) {
        const { text, data } = await twitterApi("twitter_user_info", { username: params.username }, token, signal);
        return { content: [{ type: "text" as const, text }], details: data };
      },
    },
  ];
}
