import { useState, useCallback } from 'react';

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

  const envToken = import.meta.env.VITE_DERIV_API_TOKEN?.trim() || '';
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
