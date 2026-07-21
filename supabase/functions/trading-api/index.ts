import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface TradePayload {
  market: string;
  type: string;
  direction: string;
  amount: number;
  confidence: number;
  reason?: string;
  entry_price: number;
  contract_id?: string;
}

interface AuditPayload {
  action: string;
  actor: string;
  ip_address?: string;
  details?: Record<string, unknown>;
}

function getSupabaseClient() {
  const url = Deno.env.get("SUPABASE_URL")!;
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  return { url, key };
}

async function supabaseQuery(url: string, key: string, path: string, method: string, body?: unknown) {
  const res = await fetch(`${url}/rest/v1/${path}`, {
    method,
    headers: {
      "Authorization": `Bearer ${key}`,
      "apikey": key,
      "Content-Type": "application/json",
      "Prefer": method === "POST" ? "return=representation" : "",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Supabase error ${res.status}: ${text}`);
  }
  return res.status === 204 ? null : await res.json();
}

async function verifyUser(req: Request): Promise<{ user: any; token: string } | null> {
  const authHeader = req.headers.get("Authorization");
  if (!authHeader) return null;

  const token = authHeader.replace("Bearer ", "");
  if (!token) return null;

  // Verify the JWT by calling Supabase auth.getUser
  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const res = await fetch(`${supabaseUrl}/auth/v1/user`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "apikey": Deno.env.get("SUPABASE_ANON_KEY")!,
    },
  });

  if (!res.ok) return null;

  const user = await res.json();
  return { user, token };
}

const VALID_MARKETS = new Set([
  "R_10", "R_25", "R_50", "R_75", "R_100",
  "R_10_10S", "R_25_10S", "R_50_10S", "R_75_10S", "R_100_10S",
  "R_100_25S", "R_100_50S"
]);

function sanitizeString(input: string): string {
  return input
    .replace(/[<>]/g, "")
    .replace(/javascript:/gi, "")
    .replace(/on\w+\s*=/gi, "")
    .slice(0, 500);
}

function validateTrade(payload: TradePayload): string | null {
  if (!VALID_MARKETS.has(payload.market)) return `Invalid market: ${payload.market}`;
  if (!["CALL", "PUT"].includes(payload.direction)) return "Direction must be CALL or PUT";
  if (typeof payload.amount !== "number" || payload.amount < 0.35 || payload.amount > 10000) return "Amount must be between 0.35 and 10000";
  if (typeof payload.confidence !== "number" || payload.confidence < 0 || payload.confidence > 100) return "Confidence must be 0-100";
  if (typeof payload.entry_price !== "number" || payload.entry_price <= 0) return "Invalid entry price";
  return null;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const { url, key } = getSupabaseClient();
    const path = new URL(req.url).pathname;
    const segments = path.split("/").filter(Boolean);
    const route = segments[segments.length - 1] || "";

    // Verify user for protected endpoints
    const auth = await verifyUser(req);

    // GET /trading-api/health (public)
    if (req.method === "GET" && route === "health") {
      return new Response(JSON.stringify({ status: "healthy", timestamp: new Date().toISOString() }), {
        status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // Require auth for all other endpoints
    if (!auth) {
      return new Response(JSON.stringify({ error: "Unauthorized — invalid or missing token" }), {
        status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // GET /trading-api/trades
    if (req.method === "GET" && route === "trades") {
      const data = await supabaseQuery(url, key, "trades?order=entry_time.desc&limit=100", "GET");
      return new Response(JSON.stringify(data), {
        status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // POST /trading-api/trades
    if (req.method === "POST" && route === "trades") {
      const body = await req.json() as TradePayload;
      const error = validateTrade(body);
      if (error) {
        return new Response(JSON.stringify({ error }), {
          status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
      const trade = {
        market: sanitizeString(body.market),
        type: sanitizeString(body.type || "Rise/Fall"),
        direction: sanitizeString(body.direction),
        amount: body.amount,
        confidence: body.confidence,
        reason: body.reason ? sanitizeString(body.reason) : null,
        entry_price: body.entry_price,
        entry_time: new Date().toISOString(),
        contract_id: body.contract_id ? sanitizeString(body.contract_id) : null,
      };
      const data = await supabaseQuery(url, key, "trades", "POST", trade);
      return new Response(JSON.stringify(data?.[0] || data), {
        status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // GET /trading-api/statistics
    if (req.method === "GET" && route === "statistics") {
      const data = await supabaseQuery(url, key, "trade_statistics?id=eq.1", "GET");
      return new Response(JSON.stringify(data?.[0] || {}), {
        status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // GET /trading-api/settings
    if (req.method === "GET" && route === "settings") {
      const data = await supabaseQuery(url, key, "system_settings?id=eq.1", "GET");
      return new Response(JSON.stringify(data?.[0] || {}), {
        status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // PATCH /trading-api/settings
    if (req.method === "PATCH" && route === "settings") {
      const body = await req.json() as Record<string, unknown>;
      const allowed = [
        "base_amount", "auto_trading", "max_trades_per_hour", "min_confidence",
        "stop_loss", "take_profit", "max_consecutive_losses",
        "enable_even_odd", "enable_rise_fall", "enable_over_under",
        "enable_match_diff", "enable_digit_analysis"
      ];
      const updates: Record<string, unknown> = {};
      for (const key of allowed) {
        if (body[key] !== undefined) updates[key] = body[key];
      }
      if (Object.keys(updates).length === 0) {
        return new Response(JSON.stringify({ error: "No valid fields to update" }), {
          status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
      updates.updated_at = new Date().toISOString();
      const data = await supabaseQuery(url, key, "system_settings?id=eq.1", "PATCH", updates);
      return new Response(JSON.stringify(data?.[0] || data), {
        status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // POST /trading-api/audit
    if (req.method === "POST" && route === "audit") {
      const body = await req.json() as AuditPayload;
      if (!body.action || !body.actor) {
        return new Response(JSON.stringify({ error: "action and actor are required" }), {
          status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
      const audit = {
        action: sanitizeString(body.action),
        actor: sanitizeString(body.actor),
        ip_address: body.ip_address ? sanitizeString(body.ip_address) : null,
        details: body.details || {},
        timestamp: new Date().toISOString(),
      };
      const data = await supabaseQuery(url, key, "audit_log", "POST", audit);
      return new Response(JSON.stringify(data?.[0] || data), {
        status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // GET /trading-api/audit
    if (req.method === "GET" && route === "audit") {
      const data = await supabaseQuery(url, key, "audit_log?order=timestamp.desc&limit=200", "GET");
      return new Response(JSON.stringify(data), {
        status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    return new Response(JSON.stringify({ error: "Not found" }), {
      status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" }
    });

  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message || "Internal server error" }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" }
    });
  }
});
