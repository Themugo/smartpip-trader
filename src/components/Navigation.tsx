/**
 * Navigation Components
 * 
 * Global navigation with search, command palette, breadcrumbs, and keyboard shortcuts.
 */

import { useState, useEffect, useCallback, useRef, useContext, createContext, type ReactNode } from 'react';
import { cn } from '../ui/utils';

// Icons
const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const CommandIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const HomeIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

// Types
export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: ReactNode;
}

export interface SearchResult {
  id: string;
  title: string;
  description?: string;
  category: string;
  icon?: ReactNode;
  action: () => void;
}

export interface CommandItem {
  id: string;
  label: string;
  shortcut?: string;
  icon?: ReactNode;
  category?: string;
  action: () => void;
  disabled?: boolean;
}

// Breadcrumbs Component
export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm">
      <ol className="flex items-center gap-1">
        <li>
          <a
            href="/"
            className="text-slate-400 hover:text-white transition-colors"
            aria-label="Home"
          >
            <HomeIcon />
          </a>
        </li>
        {items.map((item, index) => (
          <li key={index} className="flex items-center gap-1">
            <ChevronRightIcon />
            {item.href ? (
              <a
                href={item.href}
                className="text-slate-400 hover:text-white transition-colors flex items-center gap-1"
              >
                {item.icon}
                {item.label}
              </a>
            ) : (
              <span className="text-white flex items-center gap-1">
                {item.icon}
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

// Global Search Component
interface GlobalSearchProps {
  onSearch?: (query: string) => void;
  results?: SearchResult[];
  isOpen: boolean;
  onClose: () => void;
  placeholder?: string;
}

export function GlobalSearch({
  onSearch,
  results = [],
  isOpen,
  onClose,
  placeholder = 'Search...',
}: GlobalSearchProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (query && onSearch) {
      onSearch(query);
    }
  }, [query, onSearch]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        if (results[selectedIndex]) {
          results[selectedIndex].action();
          onClose();
        }
        break;
      case 'Escape':
        onClose();
        break;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      
      {/* Search Modal */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-2xl">
        <div
          className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
            <SearchIcon />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="flex-1 bg-transparent text-white placeholder-slate-500 outline-none text-lg"
            />
            <kbd className="px-2 py-1 text-xs text-slate-500 bg-slate-800 rounded">ESC</kbd>
          </div>

          {/* Results */}
          {results.length > 0 && (
            <div className="max-h-96 overflow-y-auto">
              {results.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => {
                    result.action();
                    onClose();
                  }}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                    index === selectedIndex
                      ? 'bg-blue-600/20 text-white'
                      : 'text-slate-300 hover:bg-slate-800'
                  )}
                >
                  {result.icon && (
                    <span className="text-slate-500">{result.icon}</span>
                  )}
                  <div className="flex-1">
                    <p className="font-medium">{result.title}</p>
                    {result.description && (
                      <p className="text-sm text-slate-500">{result.description}</p>
                    )}
                  </div>
                  <span className="text-xs text-slate-600">{result.category}</span>
                </button>
              ))}
            </div>
          )}

          {query && results.length === 0 && (
            <div className="px-4 py-8 text-center text-slate-500">
              No results found for "{query}"
            </div>
          )}

          {!query && (
            <div className="px-4 py-6 text-center text-slate-500">
              <p>Start typing to search...</p>
              <p className="text-sm mt-2">Press <kbd className="px-1.5 py-0.5 text-xs bg-slate-800 rounded">↑↓</kbd> to navigate, <kbd className="px-1.5 py-0.5 text-xs bg-slate-800 rounded">Enter</kbd> to select</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Command Palette Component
interface CommandPaletteProps {
  commands: CommandItem[];
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ commands, isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(query.toLowerCase()) ||
      cmd.category?.toLowerCase().includes(query.toLowerCase())
  );

  // Group commands by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    const category = cmd.category || 'General';
    if (!acc[category]) acc[category] = [];
    acc[category].push(cmd);
    return acc;
  }, {} as Record<string, CommandItem[]>);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        if (filteredCommands[selectedIndex] && !filteredCommands[selectedIndex].disabled) {
          filteredCommands[selectedIndex].action();
          onClose();
        }
        break;
      case 'Escape':
        onClose();
        break;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-xl">
        <div
          className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
            <CommandIcon />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Type a command..."
              className="flex-1 bg-transparent text-white placeholder-slate-500 outline-none"
            />
            <kbd className="px-2 py-1 text-xs text-slate-500 bg-slate-800 rounded">ESC</kbd>
          </div>

          {/* Commands */}
          <div className="max-h-80 overflow-y-auto py-2">
            {Object.entries(groupedCommands).map(([category, cmds]) => (
              <div key={category}>
                <div className="px-4 py-2 text-xs font-medium text-slate-500 uppercase">
                  {category}
                </div>
                {cmds.map((cmd, cmdIndex) => {
                  const globalIndex = filteredCommands.findIndex((c) => c.id === cmd.id);
                  return (
                    <button
                      key={cmd.id}
                      onClick={() => {
                        if (!cmd.disabled) {
                          cmd.action();
                          onClose();
                        }
                      }}
                      disabled={cmd.disabled}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                        globalIndex === selectedIndex
                          ? 'bg-blue-600/20 text-white'
                          : 'text-slate-300 hover:bg-slate-800',
                        cmd.disabled && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      {cmd.icon && <span className="text-slate-500">{cmd.icon}</span>}
                      <span className="flex-1">{cmd.label}</span>
                      {cmd.shortcut && (
                        <kbd className="px-2 py-0.5 text-xs text-slate-500 bg-slate-800 rounded">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}

            {filteredCommands.length === 0 && (
              <div className="px-4 py-8 text-center text-slate-500">
                No commands found
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Keyboard Shortcuts Hook
export function useKeyboardShortcuts(shortcuts: Record<string, () => void>) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      const key = [
        e.ctrlKey && 'ctrl',
        e.shiftKey && 'shift',
        e.altKey && 'alt',
        e.metaKey && 'meta',
        e.key.toLowerCase(),
      ]
        .filter(Boolean)
        .join('+');

      if (shortcuts[key]) {
        e.preventDefault();
        shortcuts[key]();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

// Navigation Provider
interface NavigationContextValue {
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  breadcrumbs: BreadcrumbItem[];
  setBreadcrumbs: (items: BreadcrumbItem[]) => void;
  recentPages: string[];
  addRecentPage: (page: string) => void;
}

const NavigationContext = createContext<NavigationContextValue | null>(null);

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);
  const [recentPages, setRecentPages] = useState<string[]>([]);

  const addRecentPage = useCallback((page: string) => {
    setRecentPages((prev) => {
      const filtered = prev.filter((p) => p !== page);
      return [page, ...filtered].slice(0, 5);
    });
  }, []);

  // Global keyboard shortcuts
  useKeyboardShortcuts({
    'ctrl+k': () => setSearchOpen(true),
    'meta+k': () => setSearchOpen(true),
    'ctrl+shift+p': () => setCommandPaletteOpen(true),
    'ctrl+p': () => setCommandPaletteOpen(true),
    escape: () => {
      setSearchOpen(false);
      setCommandPaletteOpen(false);
    },
  });

  return (
    <NavigationContext.Provider
      value={{
        searchOpen,
        setSearchOpen,
        commandPaletteOpen,
        setCommandPaletteOpen,
        breadcrumbs,
        setBreadcrumbs,
        recentPages,
        addRecentPage,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within NavigationProvider');
  }
  return context;
}

export default NavigationProvider;
