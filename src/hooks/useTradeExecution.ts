import { useState } from 'react';
import { api } from '../lib/api';

export type ContractType = 'DIGITMATCH' | 'DIGITDIFF' | 'DIGITOVER' | 'DIGITUNDER' | 'DIGITEVEN' | 'DIGITODD' | 'CALL' | 'PUT';

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

/** Canonical execution hook: browser -> authenticated backend -> Deriv. */
export function useTradeExecution(_apiToken?: string) {
  const [executing, setExecuting] = useState(false);
  const [lastResult, setLastResult] = useState<TradeResult | null>(null);
  const [openContracts, setOpenContracts] = useState<TradeResult[]>([]);

  const executeTrade = async (request: TradeRequest): Promise<TradeResult> => {
    setExecuting(true);
    setLastResult(null);
    try {
      const response = await api.executeTrade(request);
      if (!response.data || response.error) {
        const result: TradeResult = { success: false, error: response.error || 'Trade request failed' };
        setLastResult(result);
        return result;
      }
      const result = response.data;
      if (result.success && result.contract_id) {
        const open: TradeResult = {
          success: true,
          contract_id: result.contract_id,
          buy_price: result.buy_price,
          payout: result.payout,
          status: 'open',
        };
        setOpenContracts(prev => [...prev, open]);
        setLastResult(open);
        return open;
      }
      const failure: TradeResult = { success: false, error: result.error || 'Trade was not accepted' };
      setLastResult(failure);
      return failure;
    } finally {
      setExecuting(false);
    }
  };

  // Early selling remains a backend-only operation. Do not reintroduce a direct
  // browser Deriv socket here because it would bypass the central risk gate.
  const sellContract = async (_contractId: string): Promise<TradeResult> => ({
    success: false,
    error: 'Early contract selling is disabled until the backend sell route is enabled',
  });

  return { executeTrade, sellContract, executing, lastResult, openContracts };
}
