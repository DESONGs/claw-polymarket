---
name: geo-analysis
description: "Geopolitical event-driven multi-asset prediction analysis framework. Combines Twitter/News sensing, Polymarket probability signals, and asset price data into structured forecasts."

user-invocable: true
metadata:
  openclaw:
    emoji: "\U0001F30D"
  version: 1.0.0
---

# Geo-Political Analysis Framework

When the user asks about geopolitical events' impact on asset prices, requests market prediction analysis, or mentions keywords like tariffs, sanctions, central bank, election, regulation, Fed, FOMC, CPI, war, conflict — activate this framework.

## Step 1: Event Classification

Extract from the user's description or from tool data:

**Event Types** (7 categories):

| Type | Sub-types | Typical Triggers |
|------|-----------|-----------------|
| Geopolitical Conflict | Military action, sanctions escalation, territorial disputes | Troop movements, UN resolutions, sanctions lists |
| Central Bank Policy | Rate decisions, QE/QT, forward guidance | FOMC statements, ECB decisions, official speeches |
| Regulatory Policy | Crypto regulation, financial regulation, antitrust | SEC actions, congressional legislation, executive orders |
| Election & Regime | Elections, impeachment, cabinet changes | Poll shifts, candidate statements, vote results |
| Trade & Tariff | Tariff adjustments, trade agreements, sanctions | Executive orders, USTR statements, retaliation |
| Economic Data Shock | CPI surprise, jobs anomaly, GDP revision | Data release vs market expectation deviation |
| Black Swan | Pandemic, natural disaster, institutional collapse | Breaking news, emergency declarations |

**Urgency**:
- CRITICAL: probability change > 15% in 24h, requires immediate analysis
- SIGNIFICANT: probability change 5-15%, 1-7 day window
- MARGINAL: probability change < 5%, trackable over > 7 days

**Novelty**: NEW / DEVELOPMENT / ESCALATION / DE-ESCALATION

## Step 2: Parallel Data Collection

Based on event type, call these tools (as many in parallel as possible):

1. `twitter_search` keywords="{event keywords}" — real-time sentiment, key figure statements
2. `news_search` q="{event keywords}" — news coverage + AI ratings
3. `polymarket_search` query="{event keywords}" — find related prediction markets
4. For each market found, call:
   - `polymarket_midpoint` token_id=X — crowd probability consensus
   - `polymarket_spread` token_id=X — market maker confidence (when available)
   - `polymarket_price_history` token_id=X — probability trend over time (when available)
   - `polymarket_book` token_id=X — buy/sell pressure imbalance (when available)
5. `openbb_stock` symbol="{affected asset ticker}" mode=quote — current price of affected assets
6. `openbb_economy` type=calendar — upcoming economic events for context

**Affected asset tickers by event type**:
- Geopolitical Conflict: CL=F (crude oil), GC=F (gold), BTC-USD, ^GSPC (S&P 500)
- Central Bank Policy: ^GSPC, ^IXIC (NASDAQ), BTC-USD, DX-Y.NYB (USD index)
- Crypto Regulation: BTC-USD, ETH-USD
- Trade & Tariff: ^GSPC, CL=F, GC=F, relevant country ETFs
- Economic Data Shock: ^GSPC, ^IXIC, BTC-USD, GC=F

## Step 3: Three-Role Signal Interpretation

For each Polymarket position, interpret from three dimensions:

### Role 1: Crowd Wisdom (midpoint)
- midpoint = probability anchor from real-money bets
- Reliability assessment:
  - Daily volume > $50k + market age > 7 days = HIGH reliability
  - Daily volume $10k-$50k = MEDIUM reliability
  - Daily volume < $10k or new market = LOW reliability
- 20%-80% range = highest signal value; <10% or >90% = low marginal info

### Role 2: Leading Indicator (price_history)
- 1h probability change > 10% = strong signal (possible information leak)
- 3+ consecutive same-direction periods = trend confirmed
- Rapid rise from low-probability zone (<30%) = highest signal value
- Compare timing: prediction market moves often lead traditional markets by 2-6 hours

### Role 3: Sentiment Gauge (spread + book)

| Spread | Book Balance | Volume | Sentiment State |
|--------|-------------|--------|----------------|
| Narrow (<50bps) | Balanced | High | **Stable Consensus** — strong agreement on outcome |
| Narrow | Imbalanced | High | **Directional Consensus** — strong lean one way |
| Wide (>200bps) | Imbalanced | Low | **Uncertain Anxiety** — market confused, MMs retreating |
| Wide | Balanced | High | **Fierce Divergence** — bulls vs bears, volatility incoming |

## Step 4: Impact Chain Reasoning + Scenario Construction

### Impact Mapping Rules

```
Geopolitical Conflict Escalation:
  -> Safe-haven demand rises -> Gold UP, USD UP, JPY/CHF UP
  -> Energy supply concern -> Crude oil UP (if production region)
  -> Risk appetite drops -> Equities DOWN, Crypto DOWN (short-term)
  -> Supply chain disruption -> Affected commodities UP

Central Bank Hawkish Surprise:
  -> Rate expectations rise -> USD UP, Bonds DOWN
  -> Liquidity tightening -> Equities DOWN (esp. growth), Crypto DOWN
  -> Yield spread widens -> EM currencies DOWN, carry trade unwind

Crypto Regulation Positive:
  -> Compliance expectation -> BTC/ETH UP
  -> Institutional capital inflow -> Total crypto market cap UP

Trade/Tariff Escalation:
  -> Import costs rise -> Affected country currency DOWN, CPI expectations UP
  -> Retaliation cycle expected -> Global equities DOWN, Safe-havens UP
  -> Supply chain restructuring -> Beneficiary country assets UP

Economic Data Shock (hot CPI / strong jobs):
  -> Rate hike expectations rise -> Equities DOWN, USD UP
  -> Inflation hedge demand -> Gold UP, BTC UP (medium-term)
```

### Scenario Construction (3 scenarios, probabilities must sum to 100%)

For each scenario specify:
- **Trigger condition**: what must happen
- **Probability**: anchored to Polymarket midpoint + your independent judgment
- **Price target**: range for affected assets
- **Rationale**: causal chain logic

## Step 5: Output — Signal Dashboard

Structure your final output as:

### Event Assessment
- Event summary, type, novelty, urgency, market expectation (UNEXPECTED / PARTIALLY_EXPECTED / FULLY_PRICED)

### Prediction Market Signals
- Primary market question, midpoint, 24h trend, reliability
- Three-role readings (crowd wisdom / leading indicator / sentiment gauge)

### Asset Impact Map
Table: Asset | Direction (BULLISH/BEARISH/NEUTRAL) | Strength (HIGH/MED/LOW) | Transmission Path | Time Lag

### Scenario Analysis
- Bullish scenario: trigger, probability, price target, rationale
- Neutral scenario: trigger, probability, price target, rationale
- Bearish scenario: trigger, probability, price target, rationale

### Signal Dashboard
| Metric | Value |
|--------|-------|
| Direction Score | -1.0 to +1.0 |
| Confidence | HIGH / MEDIUM / LOW |
| Time Horizon | IMMEDIATE / SHORT_TERM / MEDIUM_TERM |
| Volatility Expectation | ELEVATED / NORMAL / COMPRESSED |
| **Overall Recommendation** | **concise directional summary** |

### Risk Factors
- List factors that could invalidate the analysis
- Prediction market signal limitations (liquidity, participant bias)
- Reassessment trigger point

## Important Principles

1. **Prediction markets are input, not gospel** — midpoint is a valuable anchor but reflects participant consensus, not truth
2. **Confidence > Precision** — "60% confidence in this direction" is more honest than "$85 target"
3. **Time window is part of the prediction** — every forecast must include validity period
4. **Traceability** — every conclusion must trace back to the triggering event and data
5. **PASS is a valid output** — when signal reliability is low, impact chains unclear, or scenario probabilities near-equal, outputting "insufficient signal" is more responsible than forcing a prediction
