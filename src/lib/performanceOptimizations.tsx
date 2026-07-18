/**
 * Performance Optimizations
 * 
 * Advanced performance utilities including:
 * - Lazy loading with prefetching
 * - Virtual scrolling for large lists
 * - Memoization utilities
 * - API caching layer
 * - Bundle optimization helpers
 */

import { useState, useEffect, useCallback, useRef, useMemo, type ReactNode, type ComponentType, Suspense, lazy } from 'react';

// ============================================================================
// LAZY LOADING & CODE SPLITTING
// ============================================================================

/**
 * Lazy load a component with loading fallback
 */
export function lazyLoad<T extends object>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  fallback?: ReactNode
) {
  const LazyComponent = lazy(importFn);
  
  return function LazyWrapper(props: T) {
    return (
      <Suspense fallback={fallback || <DefaultLoadingSkeleton />}>
        <LazyComponent {...(props as any)} />
      </Suspense>
    );
  };
}

/**
 * Default loading skeleton
 */
function DefaultLoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-4 bg-slate-700 rounded w-3/4" />
      <div className="h-4 bg-slate-700 rounded" />
      <div className="h-4 bg-slate-700 rounded w-5/6" />
    </div>
  );
}

// ============================================================================
// VIRTUAL SCROLLING
// ============================================================================

export interface VirtualItem {
  index: number;
  start: number;
  size: number;
  end: number;
}

export interface VirtualOptions {
  size: number;
  overscan?: number;
}

/**
 * Calculate virtual items for a list
 */
export function calculateVirtualItems(
  scrollOffset: number,
  containerSize: number,
  items: unknown[],
  options: VirtualOptions
): VirtualItem[] {
  const { size, overscan = 3 } = options;
  
  const startIndex = Math.max(0, Math.floor(scrollOffset / size) - overscan);
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollOffset + containerSize) / size) + overscan
  );
  
  const virtualItems: VirtualItem[] = [];
  
  for (let i = startIndex; i <= endIndex; i++) {
    virtualItems.push({
      index: i,
      start: i * size,
      size,
      end: (i + 1) * size,
    });
  }
  
  return virtualItems;
}

// ============================================================================
// VIRTUAL LIST HOOK
// ============================================================================

export function useVirtualList<T>(
  items: T[],
  itemHeight: number,
  containerHeight: number,
  overscan: number = 3
) {
  const [scrollTop, setScrollTop] = useState(0);
  
  const totalHeight = items.length * itemHeight;
  
  const virtualItems = useMemo(() => {
    return calculateVirtualItems(scrollTop, containerHeight, items, {
      size: itemHeight,
      overscan,
    });
  }, [scrollTop, containerHeight, items, itemHeight, overscan]);
  
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);
  
  return {
    virtualItems,
    totalHeight,
    scrollTop,
    handleScroll,
    containerHeight,
    itemHeight,
    itemCount: items.length,
  };
}

// ============================================================================
// INFINITE SCROLL
// ============================================================================

export interface UseInfiniteScrollOptions<T> {
  fetchMore: (page: number) => Promise<T[]>;
  initialData?: T[];
  threshold?: number;
}

export function useInfiniteScroll<T>({
  fetchMore,
  initialData = [],
  threshold = 100,
}: UseInfiniteScrollOptions<T>) {
  const [data, setData] = useState<T[]>(initialData);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    try {
      const nextPage = page + 1;
      const newItems = await fetchMore(nextPage);
      
      if (newItems.length === 0) {
        setHasMore(false);
      } else {
        setData(prev => [...prev, ...newItems]);
        setPage(nextPage);
      }
    } catch (error) {
      console.error('Failed to load more:', error);
    } finally {
      setLoading(false);
    }
  }, [fetchMore, page, loading, hasMore]);

  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }
    
    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          loadMore();
        }
      },
      { threshold: threshold / window.innerHeight }
    );
    
    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }
    
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [loadMore, hasMore, loading, threshold]);

  return {
    data,
    loading,
    hasMore,
    loadMoreRef,
    reset: () => {
      setData(initialData);
      setPage(1);
      setHasMore(true);
    },
  };
}

// ============================================================================
// API CACHE
// ============================================================================

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

class APICache {
  private cache: Map<string, CacheEntry<unknown>> = new Map();
  private defaultTTL = 5 * 60 * 1000; // 5 minutes

  set<T>(key: string, data: T, ttl?: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL,
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    
    if (!entry) return null;
    
    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.data;
  }

  has(key: string): boolean {
    return this.get(key) !== null;
  }

  delete(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  keys(): string[] {
    return Array.from(this.cache.keys());
  }
}

export const apiCache = new APICache();

// ============================================================================
// MEMOIZATION UTILITIES
// ============================================================================

/**
 * Create a memoized callback
 */
export function useMemoCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  deps: unknown[]
): T {
  return useCallback(callback, deps) as T;
}

/**
 * Create a memoized value with comparison
 */
export function useMemoCompare<T>(
  value: T,
  compare: (prev: T, next: T) => boolean
): T {
  const [memo, setMemo] = useState(value);
  
  useEffect(() => {
    if (!compare(memo, value)) {
      setMemo(value);
    }
  }, [value, memo, compare]);
  
  return memo;
}

/**
 * Stable equality check for objects
 */
export function useShallowCompare <T extends object>(value: T): boolean {
  const ref = useRef<T>(value);
  
  return useMemo(() => {
    const prevKeys = Object.keys(ref.current);
    const nextKeys = Object.keys(value);
    
    if (prevKeys.length !== nextKeys.length) {
      ref.current = value;
      return false;
    }
    
    for (const key of prevKeys) {
      if (ref.current[key as keyof T] !== value[key as keyof T]) {
        ref.current = value;
        return false;
      }
    }
    
    return true;
  }, [value]);
}

// ============================================================================
// PREFETCHING
// ============================================================================

/**
 * Prefetch a resource
 */
export function prefetch(url: string, as: 'script' | 'style' | 'image' | 'fetch' = 'fetch'): void {
  if (typeof window === 'undefined') return;
  
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.href = url;
  link.as = as;
  
  if (as === 'image') {
    link.as = 'image';
  }
  
  document.head.appendChild(link);
}

/**
 * Preload a critical resource
 */
export function preload(url: string, as: 'script' | 'style' | 'image' | 'font' | 'document'): void {
  if (typeof window === 'undefined') return;
  
  const link = document.createElement('link');
  link.rel = 'preload';
  link.href = url;
  link.as = as;
  
  if (as === 'font') {
    link.crossOrigin = 'anonymous';
  }
  
  document.head.appendChild(link);
}

/**
 * Prefetch route on hover
 */
export function usePrefetchOnHover(routes: string[]) {
  const prefetched = useRef<Set<string>>(new Set());
  
  useEffect(() => {
    const prefetchRoute = (route: string) => {
      if (prefetched.current.has(route)) return;
      prefetched.current.add(route);
      preload(route, 'document');
    };
    
    const handleMouseEnter = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const link = target.closest('a');
      
      if (link) {
        const href = link.getAttribute('href');
        if (href && routes.some(r => href.startsWith(r))) {
          prefetchRoute(href);
        }
      }
    };
    
    document.addEventListener('mouseenter', handleMouseEnter, true);
    return () => document.removeEventListener('mouseenter', handleMouseEnter, true);
  }, [routes]);
}

// ============================================================================
// DEBOUNCE & THROTTLE
// ============================================================================

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
}

export function useThrottle<T>(value: T, limit: number): T {
  const [throttledValue, setThrottledValue] = useState(value);
  const lastRan = useRef(Date.now());
  
  useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan.current >= limit) {
        setThrottledValue(value);
        lastRan.current = Date.now();
      }
    }, limit - (Date.now() - lastRan.current));
    
    return () => clearTimeout(handler);
  }, [value, limit]);
  
  return throttledValue;
}

// ============================================================================
// PERFORMANCE METRICS
// ============================================================================

export interface PerformanceMetrics {
  fcp: number | null;
  lcp: number | null;
  fid: number | null;
  cls: number | null;
  ttfb: number | null;
  loadTime: number | null;
}

export function usePerformanceMetrics(): PerformanceMetrics {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fcp: null,
    lcp: null,
    fid: null,
    cls: null,
    ttfb: null,
    loadTime: null,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const loadTime = performance.now();
    
    window.addEventListener('load', () => {
      const timing = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      
      setMetrics(prev => ({
        ...prev,
        ttfb: timing.responseStart - timing.requestStart,
        loadTime: performance.now() - loadTime,
      }));
    });

    // LCP
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1] as PerformanceEntry & { startTime: number };
      setMetrics(prev => ({ ...prev, lcp: lastEntry?.startTime || null }));
    });
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

    // FID
    const fidObserver = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if ('processingStart' in entry) {
          const fid = (entry as PerformanceEventTiming).processingStart - entry.startTime;
          setMetrics(prev => ({ ...prev, fid }));
        }
      });
    });
    fidObserver.observe({ entryTypes: ['first-input'] });

    // CLS
    let clsValue = 0;
    const clsObserver = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        const hasInput = 'hadRecentInput' in entry && !(entry as { hadRecentInput: boolean }).hadRecentInput;
        if (hasInput) {
          const layoutEntry = entry as PerformanceEntry & { value: number; hadRecentInput: boolean };
          clsValue += layoutEntry.value;
          setMetrics(prev => ({ ...prev, cls: clsValue }));
        }
      });
    });
    clsObserver.observe({ entryTypes: ['layout-shift'] });

    return () => {
      lcpObserver.disconnect();
      fidObserver.disconnect();
      clsObserver.disconnect();
    };
  }, []);

  return metrics;
}

// ============================================================================
// BUNDLE ANALYSIS
// ============================================================================

export interface BundleStats {
  totalSize: number;
  gzipSize: number;
  modules: number;
}

export function getBundleStats(): BundleStats {
  // In production, this would be populated by webpack-bundle-analyzer
  return {
    totalSize: 0,
    gzipSize: 0,
    modules: 0,
  };
}

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  lazyLoad,
  useVirtualList,
  useInfiniteScroll,
  apiCache,
  prefetch,
  preload,
  usePrefetchOnHover,
  useDebounce,
  useThrottle,
  usePerformanceMetrics,
  getBundleStats,
  calculateVirtualItems,
};
