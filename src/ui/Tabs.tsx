/**
 * Tabs Component
 * 
 * Accessible tab navigation component.
 */

import { useState, type ReactNode } from 'react';
import { cn } from './utils';

export interface Tab {
  id: string;
  label: string;
  icon?: ReactNode;
  disabled?: boolean;
  content: ReactNode;
}

export interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  variant?: 'default' | 'pills' | 'underline';
  fullWidth?: boolean;
  className?: string;
}

export function Tabs({
  tabs,
  defaultTab,
  onChange,
  variant = 'default',
  fullWidth = false,
  className,
}: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const handleTabClick = (tabId: string, disabled?: boolean) => {
    if (disabled) return;
    setActiveTab(tabId);
    onChange?.(tabId);
  };

  const activeContent = tabs.find((tab) => tab.id === activeTab)?.content;

  const variantStyles = {
    default: {
      container: 'bg-slate-800 rounded-lg p-1',
      tab: 'px-4 py-2 text-sm font-medium rounded-md transition-colors',
      active: 'bg-slate-700 text-white',
      inactive: 'text-slate-400 hover:text-white',
    },
    pills: {
      container: 'gap-1',
      tab: 'px-4 py-2 text-sm font-medium rounded-full transition-colors',
      active: 'bg-blue-600 text-white',
      inactive: 'text-slate-400 hover:text-white hover:bg-slate-800',
    },
    underline: {
      container: 'border-b border-slate-800',
      tab: 'px-4 py-2 text-sm font-medium transition-colors border-b-2 border-transparent -mb-px',
      active: 'text-blue-400 border-blue-400',
      inactive: 'text-slate-400 hover:text-white',
    },
  };

  const styles = variantStyles[variant];

  return (
    <div className={className}>
      {/* Tab list */}
      <div
        role="tablist"
        className={cn(
          'flex',
          variant !== 'underline' && styles.container,
          fullWidth && variant === 'pills' && 'w-full',
          variant !== 'underline' && 'flex-wrap'
        )}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            id={`tab-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => handleTabClick(tab.id, tab.disabled)}
            className={cn(
              styles.tab,
              fullWidth && 'flex-1 flex justify-center',
              styles[activeTab === tab.id ? 'active' : 'inactive'],
              tab.disabled && 'opacity-50 cursor-not-allowed',
              variant === 'underline' && 'flex items-center gap-2'
            )}
          >
            {tab.icon && <span className="flex-shrink-0">{tab.icon}</span>}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeContent && (
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
          className="mt-4"
        >
          {activeContent}
        </div>
      )}
    </div>
  );
}

// Vertical tabs variant
export interface VerticalTabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  className?: string;
}

export function VerticalTabs({
  tabs,
  defaultTab,
  onChange,
  className,
}: VerticalTabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const handleTabClick = (tabId: string, disabled?: boolean) => {
    if (disabled) return;
    setActiveTab(tabId);
    onChange?.(tabId);
  };

  const activeContent = tabs.find((tab) => tab.id === activeTab)?.content;

  return (
    <div className={cn('flex gap-6', className)}>
      {/* Tab list */}
      <div
        role="tablist"
        className="flex flex-col gap-1 min-w-[200px]"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            disabled={tab.disabled}
            onClick={() => handleTabClick(tab.id, tab.disabled)}
            className={cn(
              'flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors text-left',
              activeTab === tab.id
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800',
              tab.disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            {tab.icon && <span className="flex-shrink-0">{tab.icon}</span>}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div
        role="tabpanel"
        className="flex-1"
      >
        {activeContent}
      </div>
    </div>
  );
}

export default Tabs;
