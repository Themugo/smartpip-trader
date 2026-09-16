import { useState, useCallback } from 'react';

/**
 * Broker credential state is intentionally memory-only. Never persist a Deriv
 * API token in localStorage or expose it through a Vite VITE_* variable.
 */
export function useDerivToken(isAuthenticated: boolean) {
  const [userToken, setUserTokenState] = useState('');

  const setUserToken = useCallback((token: string) => {
    setUserTokenState(token.trim());
  }, []);

  const tradingToken = isAuthenticated && userToken ? userToken : undefined;

  return {
    userToken,
    setUserToken,
    tradingToken,
    hasTradingToken: Boolean(tradingToken),
  };
}
