import { useState, useEffect, useCallback, useRef } from 'react';

interface NetworkStatus {
  online: boolean;
  lastOffline: number | null;
  wasOffline: boolean;
  since: number;
}

export function useNetworkStatus(): NetworkStatus & { waitForOnline: () => Promise<void> } {
  const [status, setStatus] = useState<NetworkStatus>(() => ({
    online: navigator.onLine,
    lastOffline: null,
    wasOffline: false,
    since: Date.now(),
  }));

  const waitersRef = useRef<(() => void)[]>([]);

  const waitForOnline = useCallback(() => {
    if (navigator.onLine) return Promise.resolve();
    return new Promise<void>((resolve) => {
      waitersRef.current.push(resolve);
    });
  }, []);

  useEffect(() => {
    const handleOnline = () => {
      setStatus((prev) => ({
        online: true,
        lastOffline: prev.online ? null : prev.since,
        wasOffline: !prev.online || prev.wasOffline,
        since: Date.now(),
      }));
      waitersRef.current.forEach((r) => r());
      waitersRef.current = [];
    };

    const handleOffline = () => {
      setStatus((prev) => ({
        online: false,
        lastOffline: prev.online ? Date.now() : prev.lastOffline,
        wasOffline: prev.wasOffline,
        since: Date.now(),
      }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      waitersRef.current.forEach((r) => r());
      waitersRef.current = [];
    };
  }, []);

  return { ...status, waitForOnline };
}
