import { useEffect, useState } from 'react';
import { Activity, Gauge, Zap, Clock } from 'lucide-react';
import { measureWebVitals, reportMetrics } from '../lib/performance';

interface PerformanceMetrics {
  fcp: number;
  lcp: number;
  fid: number;
  cls: number;
  ttfb: number;
  loadTime: number;
  bundleSize: number;
}

interface PerformanceMonitorProps {
  showOnLoad?: boolean;
}

export function PerformanceMonitor({ showOnLoad = false }: PerformanceMonitorProps) {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [isVisible, setIsVisible] = useState(showOnLoad);

  useEffect(() => {
    // Measure performance on mount
    measureWebVitals().then((perfMetrics) => {
      setMetrics(perfMetrics);
      reportMetrics(perfMetrics);
    });
  }, []);

  const getScore = (value: number, thresholds: { good: number; poor: number }): 'good' | 'needs-improvement' | 'poor' => {
    if (value <= thresholds.good) return 'good';
    if (value <= thresholds.poor) return 'needs-improvement';
    return 'poor';
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatMs = (ms: number): string => {
    return `${ms.toFixed(0)}ms`;
  };

  const getScoreColor = (score: 'good' | 'needs-improvement' | 'poor'): string => {
    switch (score) {
      case 'good': return 'text-emerald-400';
      case 'needs-improvement': return 'text-amber-400';
      case 'poor': return 'text-red-400';
    }
  };

  if (!isVisible || !metrics) return null;

  const metricsList = [
    { 
      label: 'First Contentful Paint', 
      value: metrics.fcp, 
      unit: 'ms',
      thresholds: { good: 1800, poor: 3000 },
      icon: Zap
    },
    { 
      label: 'Largest Contentful Paint', 
      value: metrics.lcp, 
      unit: 'ms',
      thresholds: { good: 2500, poor: 4000 },
      icon: Activity
    },
    { 
      label: 'First Input Delay', 
      value: metrics.fid, 
      unit: 'ms',
      thresholds: { good: 100, poor: 300 },
      icon: Gauge
    },
    { 
      label: 'Cumulative Layout Shift', 
      value: metrics.cls, 
      unit: '',
      thresholds: { good: 0.1, poor: 0.25 },
      icon: Activity,
      isDecimal: true
    },
    { 
      label: 'Time to First Byte', 
      value: metrics.ttfb, 
      unit: 'ms',
      thresholds: { good: 800, poor: 1800 },
      icon: Clock
    },
    { 
      label: 'Page Load Time', 
      value: metrics.loadTime, 
      unit: 'ms',
      thresholds: { good: 2500, poor: 4000 },
      icon: Clock
    },
  ];

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-slate-900/95 backdrop-blur-sm rounded-xl border border-slate-700 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-white">Performance</span>
        </div>
        <button
          onClick={() => setIsVisible(false)}
          className="text-slate-500 hover:text-white text-xs"
        >
          ✕
        </button>
      </div>

      {/* Metrics */}
      <div className="p-3 space-y-2">
        {metricsList.map((metric) => {
          const score = metric.isDecimal 
            ? getScore(metric.value, metric.thresholds as any)
            : getScore(metric.value, metric.thresholds);
          
          return (
            <div key={metric.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <metric.icon className="w-4 h-4 text-slate-500" />
                <span className="text-xs text-slate-400">{metric.label}</span>
              </div>
              <span className={`text-xs font-medium ${getScoreColor(score)}`}>
                {metric.isDecimal ? metric.value.toFixed(3) : formatMs(metric.value)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Bundle Size */}
      <div className="px-3 pb-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Bundle Size (est.)</span>
          <span className="text-slate-400">{formatBytes(metrics.bundleSize)}</span>
        </div>
      </div>
    </div>
  );
}

// Performance wrapper for lazy components
interface PerformanceWrapperProps {
  children: React.ReactNode;
  name: string;
}

export function PerformanceWrapper({ children, name }: PerformanceWrapperProps) {
  const startTime = performance.now();

  useEffect(() => {
    const loadTime = performance.now() - startTime;
    if (import.meta.env.DEV) {
      console.log(`[Performance] ${name} loaded in ${loadTime.toFixed(2)}ms`);
    }
  }, []);

  return <>{children}</>;
}
