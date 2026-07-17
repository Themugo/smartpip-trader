// Performance monitoring utilities for SmartPip Trader

export interface PerformanceMetrics {
  fcp: number; // First Contentful Paint
  lcp: number; // Largest Contentful Paint
  fid: number; // First Input Delay
  cls: number; // Cumulative Layout Shift
  ttfb: number; // Time to First Byte
  loadTime: number;
  bundleSize: number;
}

export interface ResourceTiming {
  name: string;
  duration: number;
  size: number;
  type: string;
}

// Core Web Vitals measurement
export function measureWebVitals(): Promise<PerformanceMetrics> {
  return new Promise((resolve) => {
    const metrics: Partial<PerformanceMetrics> = {};
    
    // Use Performance Observer API if available
    if ('PerformanceObserver' in window) {
      // Largest Contentful Paint
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1] as any;
        metrics.lcp = lastEntry?.renderTime || lastEntry?.loadTime || 0;
      }).observe({ type: 'largest-contentful-paint', buffered: true });

      // First Input Delay
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        metrics.fid = (entries[0] as any).processingStart - entries[0].startTime;
      }).observe({ type: 'first-input', buffered: true });

      // Cumulative Layout Shift
      new PerformanceObserver((list) => {
        let cls = 0;
        list.getEntries().forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            cls += entry.value;
          }
        });
        metrics.cls = cls;
      }).observe({ type: 'layout-shift', buffered: true });
    }

    // Get navigation timing
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (navigation) {
      metrics.ttfb = navigation.responseStart - navigation.requestStart;
      metrics.loadTime = navigation.loadEventEnd - navigation.startTime;
    }

    // Calculate FCP from paint timing
    const paintEntries = performance.getEntriesByType('paint');
    const fcpEntry = paintEntries.find((entry) => entry.name === 'first-contentful-paint');
    if (fcpEntry) {
      metrics.fcp = fcpEntry.startTime;
    }

    // Estimate bundle size
    metrics.bundleSize = estimateBundleSize();

    // Resolve after a delay to ensure all metrics are collected
    setTimeout(() => {
      resolve({
        fcp: metrics.fcp || 0,
        lcp: metrics.lcp || 0,
        fid: metrics.fid || 0,
        cls: metrics.cls || 0,
        ttfb: metrics.ttfb || 0,
        loadTime: metrics.loadTime || 0,
        bundleSize: metrics.bundleSize || 0,
      });
    }, 3000);
  });
}

// Estimate JavaScript bundle size
function estimateBundleSize(): number {
  const scripts = document.querySelectorAll('script[src]');
  let totalSize = 0;
  
  scripts.forEach((script) => {
    // This is an approximation - real size would come from network timing
    const src = script.getAttribute('src') || '';
    if (src.includes('main') || src.includes('chunk')) {
      totalSize += 150000; // Assume ~150KB per chunk
    }
  });
  
  return totalSize;
}

// Get resource timing data
export function getResourceTimings(): ResourceTiming[] {
  const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
  
  return resources.map((resource) => ({
    name: resource.name,
    duration: resource.duration,
    size: resource.transferSize || 0,
    type: getResourceType(resource.name),
  }));
}

function getResourceType(url: string): string {
  if (url.endsWith('.js')) return 'script';
  if (url.endsWith('.css')) return 'style';
  if (url.match(/\.(png|jpg|jpeg|gif|svg|webp)/)) return 'image';
  if (url.match(/\.(woff|woff2|ttf|otf)/)) return 'font';
  if (url.match(/\.(mp4|webm)/)) return 'video';
  return 'other';
}

// Memory usage (if available)
export function getMemoryUsage(): { used: number; total: number } | null {
  const perf = performance as any;
  if (perf.memory) {
    return {
      used: perf.memory.usedJSHeapSize,
      total: perf.memory.totalJSHeapSize,
    };
  }
  return null;
}

// Report metrics to analytics
export function reportMetrics(metrics: PerformanceMetrics): void {
  // In production, send to analytics service
  if (import.meta.env.PROD) {
    console.log('[Performance]', metrics);
    
    // Example: Send to console in production for debugging
    const perfData = {
      page: window.location.pathname,
      timestamp: Date.now(),
      metrics,
    };
    
    // Would normally send to analytics endpoint
    localStorage.setItem('perf_metrics', JSON.stringify(perfData));
  }
}

// Lazy load component helper
export function lazyLoad<T>(
  importFn: () => Promise<{ default: React.ComponentType<T> }>
): React.LazyExoticComponent<React.ComponentType<T>> {
  // Using dynamic import to avoid React UMD global issue
  return { $$typeof: Symbol.for('react.lazy'), _payload: importFn, _result: undefined } as any;
}

// Debounce utility
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Throttle utility
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// Virtual list helper for large datasets
export function createVirtualList<T>(
  items: T[],
  itemHeight: number,
  containerHeight: number
): { startIndex: number; endIndex: number; offsetY: number } {
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const scrollTop = window.scrollY;
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - 2);
  const endIndex = Math.min(items.length, startIndex + visibleCount + 4);
  const offsetY = startIndex * itemHeight;
  
  return { startIndex, endIndex, offsetY };
}

// Image lazy loading
export function lazyLoadImage(img: HTMLImageElement): void {
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const src = img.dataset.src;
            if (src) {
              img.src = src;
              img.removeAttribute('data-src');
              observer.unobserve(img);
            }
          }
        });
      },
      { rootMargin: '50px' }
    );
    
    observer.observe(img);
  } else {
    // Fallback: load immediately
    const src = img.dataset.src;
    if (src) {
      img.src = src;
    }
  }
}

// Preload critical resources
export function preloadCriticalResources(): void {
  // Preload fonts
  const fonts = ['Inter'];
  fonts.forEach((font) => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = `https://fonts.googleapis.com/css2?family=${font}:wght@400;500;600;700&display=swap`;
    link.as = 'style';
    document.head.appendChild(link);
  });
  
  // Preload critical chunks
  const criticalChunks = ['main', 'chunk-vendors'];
  criticalChunks.forEach((chunk) => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = `/assets/${chunk}.js`;
    link.as = 'script';
    document.head.appendChild(link);
  });
}

// Performance mark for custom timing
export function mark(label: string): void {
  if ('performance' in window) {
    performance.mark(label);
  }
}

// Performance measure between two marks
export function measure(label: string, startMark: string, endMark?: string): number {
  if ('performance' in window) {
    performance.measure(label, startMark, endMark);
    const entries = performance.getEntriesByName(label);
    return entries[entries.length - 1]?.duration || 0;
  }
  return 0;
}
