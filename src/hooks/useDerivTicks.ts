import { useState, useEffect, useRef, useCallback } from 'react';

export interface TickData {
  price: number;
  lastDigit: number;
  digitHistory: number[];
  priceHistory: number[];
  symbol: string;
  connected: boolean;
  authorized: boolean;
  error: string | null;
  tickCount: number;
  latencyMs: number;
}

const DERIV_WS_URL = import.meta.env.VITE_DERIV_PUBLIC_WS_URL || 'wss://api.derivws.com/trading/v1/options/ws/public';
const MAX_HISTORY = 100;

export function useDerivTicks(symbol: string = 'R_100') {
  const [tickData, setTickData] = useState<TickData>({
    price: 0,
    lastDigit: 0,
    digitHistory: [],
    priceHistory: [],
    symbol,
    connected: false,
    authorized: false,
    error: null,
    tickCount: 0,
    latencyMs: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isManualClose = useRef(false);
  const reconnectAttempt = useRef(0);
  const lastTickTime = useRef<number>(0);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const symbolRef = useRef(symbol);
  const subscriptionIdRef = useRef<string | number | null>(null);
  const requestIdRef = useRef(1);

  // Keep symbolRef in sync
  useEffect(() => {
    symbolRef.current = symbol;
  }, [symbol]);

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }, []);

  const subscribeToTicks = useCallback((requestedSymbol = symbolRef.current) => {
    const reqId = requestIdRef.current++;
    send({ ticks: requestedSymbol, subscribe: 1, req_id: reqId });
  }, [send]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }
    if (isManualClose.current) return;

    try {
      const ws = new WebSocket(DERIV_WS_URL);
      wsRef.current = ws;
      const startTime = Date.now();

      ws.onopen = () => {
        reconnectAttempt.current = 0;
        setTickData((prev) => ({
          ...prev,
          connected: true,
          error: null,
          latencyMs: Date.now() - startTime,
        }));

        // Public tick stream — no authorization required for market data
        subscribeToTicks();

        // Start ping interval
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          send({ ping: 1 });
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const now = Date.now();

          // Handle ping response
          if (data.pong) return;

          if (data.error) {
            setTickData((prev) => ({ ...prev, error: data.error.message || 'Deriv API error' }));
            return;
          }

          if (data.tick) {
            if (data.subscription?.id != null) subscriptionIdRef.current = data.subscription.id;
            const price = parseFloat(data.tick.quote);
            const displayQuote = String(data.tick.display_value ?? data.tick.quote);
            const digitsOnly = displayQuote.replace(/[^0-9]/g, '');
            const lastDigit = digitsOnly ? Number(digitsOnly.slice(-1)) : 0;
            const latency = lastTickTime.current ? now - lastTickTime.current : 0;
            lastTickTime.current = now;

            setTickData((prev) => {
              const newHistory = [...prev.digitHistory, lastDigit];
              const newPriceHistory = [...prev.priceHistory, price];
              if (newHistory.length > MAX_HISTORY) newHistory.shift();
              if (newPriceHistory.length > MAX_HISTORY) newPriceHistory.shift();
              return {
                ...prev,
                price,
                lastDigit,
                digitHistory: newHistory,
                priceHistory: newPriceHistory,
                symbol: data.tick.symbol || data.tick.underlying_symbol || prev.symbol,
                connected: true,
                error: null,
                tickCount: prev.tickCount + 1,
                latencyMs: latency > 0 && latency < 5000 ? latency : prev.latencyMs,
              };
            });
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onerror = () => {
        setTickData((prev) => ({
          ...prev,
          connected: false,
          error: 'WebSocket error. Reconnecting...',
        }));
      };

      ws.onclose = () => {
        subscriptionIdRef.current = null;
        setTickData((prev) => ({ ...prev, connected: false, authorized: false }));
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        if (!isManualClose.current) {
          const backoff = Math.min(3000 * Math.pow(2, reconnectAttempt.current), 30000);
          reconnectAttempt.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, backoff);
        }
      };
    } catch (err: unknown) {
      setTickData((prev) => ({
        ...prev,
        connected: false,
        error: err instanceof Error ? err.message : 'Failed to connect',
      }));
    }
  }, [send, subscribeToTicks]);

  const disconnect = useCallback(() => {
    isManualClose.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const switchSymbol = useCallback(
    (newSymbol: string) => {
      if (subscriptionIdRef.current != null) {
        send({ forget: subscriptionIdRef.current });
        subscriptionIdRef.current = null;
      }
      symbolRef.current = newSymbol;
      setTickData((prev) => ({
        ...prev,
        symbol: newSymbol,
        price: 0,
        lastDigit: 0,
        digitHistory: [],
        priceHistory: [],
        tickCount: 0,
        error: null,
      }));
      window.setTimeout(() => subscribeToTicks(newSymbol), 50);
    },
    [send, subscribeToTicks]
  );

  useEffect(() => {
    isManualClose.current = false;
    reconnectAttempt.current = 0;
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { tickData, switchSymbol, reconnect: connect, send };
}
