import { useState, useEffect, useRef, useCallback } from 'react';

export interface TickData {
  price: number;
  lastDigit: number;
  digitHistory: number[];
  symbol: string;
  connected: boolean;
  authorized: boolean;
  error: string | null;
  tickCount: number;
  latencyMs: number;
}

const DERIV_WS_URL = 'wss://ws.binaryws.com/websockets/v3?app_id=1089';
const MAX_HISTORY = 100;

export function useDerivTicks(symbol: string = 'R_100', apiToken?: string) {
  const [tickData, setTickData] = useState<TickData>({
    price: 0,
    lastDigit: 0,
    digitHistory: [],
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

  const subscribeToTicks = useCallback(() => {
    send({ ticks: symbolRef.current, subscribe: 1 });
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

        // Authorize if token provided
        if (apiToken) {
          send({ authorize: apiToken });
        } else {
          // For demo/public access, just subscribe to ticks
          subscribeToTicks();
        }

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

          // Handle authorization
          if (data.authorize) {
            setTickData((prev) => ({ ...prev, authorized: true }));
            subscribeToTicks();
            return;
          }

          if (data.error) {
            const msg = data.error.message || 'Deriv API error';
            // Don't show auth errors as critical if we're in public mode
            if (msg.includes('Invalid token') && !apiToken) {
              subscribeToTicks();
              return;
            }
            setTickData((prev) => ({ ...prev, error: msg }));
            return;
          }

          if (data.tick) {
            const price = parseFloat(data.tick.quote);
            const priceStr = price.toFixed(4);
            const lastDigit = parseInt(priceStr.slice(-1), 10);
            const latency = lastTickTime.current ? now - lastTickTime.current : 0;
            lastTickTime.current = now;

            setTickData((prev) => {
              const newHistory = [...prev.digitHistory, lastDigit];
              if (newHistory.length > MAX_HISTORY) newHistory.shift();
              return {
                ...prev,
                price,
                lastDigit,
                digitHistory: newHistory,
                symbol: data.tick.symbol || prev.symbol,
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
    } catch (err: any) {
      setTickData((prev) => ({
        ...prev,
        connected: false,
        error: err.message || 'Failed to connect',
      }));
    }
  }, [apiToken, send, subscribeToTicks]);

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
      // Unsubscribe from current
      send({ ticks: symbolRef.current, subscribe: 0 });
      // Update ref and state
      symbolRef.current = newSymbol;
      setTickData((prev) => ({
        ...prev,
        symbol: newSymbol,
        price: 0,
        lastDigit: 0,
        digitHistory: [],
        tickCount: 0,
      }));
      // Subscribe to new
      setTimeout(() => {
        send({ ticks: newSymbol, subscribe: 1 });
      }, 100);
    },
    [send]
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
