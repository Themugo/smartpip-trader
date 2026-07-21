import { useState, useCallback, useRef } from 'react';

export type ContractType = 'DIGITMATCH' | 'DIGITDIFF' | 'DIGITOVER' | 'DIGITUNDER' | 'DIGITEVEN' | 'DIGITODD';

export interface TradeRequest {
  contract_type: ContractType;
  symbol: string;
  amount: number;
  duration: number;
  duration_unit: 't' | 's' | 'm';
  barrier?: string;
  prediction?: string;
}

export interface TradeResult {
  success: boolean;
  contract_id?: string;
  buy_price?: number;
  payout?: number;
  error?: string;
  status?: 'open' | 'won' | 'lost' | 'sold';
  profit?: number;
}

const DERIV_WS_URL = 'wss://ws.binaryws.com/websockets/v3?app_id=1089';

export function useTradeExecution(apiToken?: string) {
  const [executing, setExecuting] = useState(false);
  const [lastResult, setLastResult] = useState<TradeResult | null>(null);
  const [openContracts, setOpenContracts] = useState<TradeResult[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const send = useCallback((ws: WebSocket, msg: object) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }, []);

  const executeTrade = useCallback(async (request: TradeRequest): Promise<TradeResult> => {
    if (!apiToken) {
      return { success: false, error: 'API token required for trading. Set VITE_DERIV_API_TOKEN in .env' };
    }

    setExecuting(true);
    setLastResult(null);

    return new Promise((resolve) => {
      try {
        const ws = new WebSocket(DERIV_WS_URL);
        wsRef.current = ws;
        let authorized = false;
        let timeout: ReturnType<typeof setTimeout> | null = null;

        const cleanup = () => {
          if (timeout) clearTimeout(timeout);
          if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
            ws.close();
          }
          wsRef.current = null;
        };

        timeout = setTimeout(() => {
          cleanup();
          setExecuting(false);
          resolve({ success: false, error: 'Trade timeout: no response from Deriv API' });
        }, 15000);

        ws.onopen = () => {
          send(ws, { authorize: apiToken });
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.error) {
              cleanup();
              setExecuting(false);
              resolve({ success: false, error: data.error.message || 'API error' });
              return;
            }

            if (data.authorize) {
              authorized = true;
              // Build the proposal request
              const proposalReq: any = {
                proposal: 1,
                amount: request.amount,
                basis: 'stake',
                contract_type: request.contract_type,
                currency: 'USD',
                duration: request.duration,
                duration_unit: request.duration_unit,
                symbol: request.symbol,
              };
              if (request.barrier !== undefined) proposalReq.barrier = request.barrier;
              send(ws, proposalReq);
              return;
            }

            if (data.proposal) {
              // Buy the contract
              send(ws, {
                buy: data.proposal.id,
                price: data.proposal.ask_price,
              });
              return;
            }

            if (data.buy) {
              const result: TradeResult = {
                success: true,
                contract_id: data.buy.contract_id?.toString(),
                buy_price: data.buy.buy_price,
                payout: data.buy.payout,
                status: 'open',
              };
              cleanup();
              setExecuting(false);
              setLastResult(result);
              setOpenContracts((prev) => [...prev, result]);
              resolve(result);
              return;
            }

            if (data.proposal_open_contract) {
              // Contract update (win/loss)
              const contract = data.proposal_open_contract;
              if (contract.is_sold) {
                const result: TradeResult = {
                  success: true,
                  contract_id: contract.contract_id?.toString(),
                  buy_price: contract.buy_price,
                  payout: contract.payout,
                  status: contract.profit >= 0 ? 'won' : 'lost',
                  profit: contract.profit,
                };
                setOpenContracts((prev) =>
                  prev.filter((c) => c.contract_id !== contract.contract_id?.toString())
                );
                setLastResult(result);
              }
            }
          } catch {
            // Ignore malformed messages
          }
        };

        ws.onerror = () => {
          cleanup();
          setExecuting(false);
          resolve({ success: false, error: 'WebSocket error during trade execution' });
        };

        ws.onclose = () => {
          if (!authorized) {
            cleanup();
            setExecuting(false);
            resolve({ success: false, error: 'Connection closed before trade completed' });
          }
        };
      } catch (err: unknown) {
        setExecuting(false);
        resolve({ success: false, error: err instanceof Error ? err.message : 'Failed to execute trade' });
      }
    });
  }, [apiToken, send]);

  const sellContract = useCallback(async (contractId: string): Promise<TradeResult> => {
    if (!apiToken) {
      return { success: false, error: 'API token required' };
    }

    return new Promise((resolve) => {
      try {
        const ws = new WebSocket(DERIV_WS_URL);
        let timeout: ReturnType<typeof setTimeout> | null = null;

        const cleanup = () => {
          if (timeout) clearTimeout(timeout);
          ws.close();
        };

        timeout = setTimeout(() => {
          cleanup();
          resolve({ success: false, error: 'Sell timeout' });
        }, 10000);

        ws.onopen = () => {
          ws.send(JSON.stringify({ authorize: apiToken }));
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);

          if (data.error) {
            cleanup();
            resolve({ success: false, error: data.error.message });
            return;
          }

          if (data.authorize) {
            ws.send(JSON.stringify({ sell: contractId }));
            return;
          }

          if (data.sell) {
            cleanup();
            resolve({
              success: true,
              contract_id: contractId,
              status: 'sold',
              profit: data.sell.sold_for - (data.sell.buy_price || 0),
            });
          }
        };

        ws.onerror = () => {
          cleanup();
          resolve({ success: false, error: 'WebSocket error' });
        };
      } catch (err: unknown) {
        resolve({ success: false, error: err instanceof Error ? err.message : 'Unknown error' });
      }
    });
  }, [apiToken]);

  return { executeTrade, sellContract, executing, lastResult, openContracts };
}
