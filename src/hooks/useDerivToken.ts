import { useState, useCallback } from 'react';
import { VITE_DERIV_API_TOKEN } from '../lib/env';

const STORAGE_KEY = 'smartpip_deriv_token';

export function useDerivToken(isAuthenticated: boolean) {
  const [userToken, setUserTokenState] = useState(
    () => localStorage.getItem(STORAGE_KEY) || ''
  );

  const setUserToken = useCallback((token: string) => {
    const trimmed = token.trim();
    if (trimmed) {
      localStorage.setItem(STORAGE_KEY, trimmed);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    setUserTokenState(trimmed);
  }, []);

  const envToken = VITE_DERIV_API_TOKEN;
  const tradingToken = isAuthenticated
    ? userToken || envToken || undefined
    : undefined;

  return {
    userToken,
    setUserToken,
    tradingToken,
    hasTradingToken: Boolean(tradingToken),
  };
}
