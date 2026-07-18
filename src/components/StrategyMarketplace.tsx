import { useState } from 'react';
import {
  Search,

  Star,
  Download,
  Upload,
  Copy,
  Heart,
  Share2,

  TrendingUp,
  Users,



  CheckCircle2,

  Tag,
  GitBranch
} from 'lucide-react';

interface Strategy {
  id: string;
  name: string;
  author: string;
  authorAvatar: string;
  description: string;
  category: string;
  tags: string[];
  rating: number;
  reviews: number;
  downloads: number;
  winRate: number;
  sharpeRatio: number;
  maxDrawdown: number;
  version: string;
  lastUpdated: string;
  price: number;
  verified: boolean;
  featured: boolean;
}

export function StrategyMarketplace() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'rating' | 'downloads' | 'newest'>('rating');
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);

  const categories = [
    { id: 'all', label: 'All Strategies' },
    { id: 'digit', label: 'Digit Patterns' },
    { id: 'trend', label: 'Trend Following' },
    { id: 'mean-reversion', label: 'Mean Reversion' },
    { id: 'breakout', label: 'Breakout' },
    { id: 'grid', label: 'Grid Trading' },
    { id: 'martingale', label: 'Martingale' },
  ];

  const strategies: Strategy[] = [
    {
      id: '1',
      name: 'Digit Master Pro',
      author: 'SmartPip Team',
      authorAvatar: 'S',
      description: 'Advanced digit pattern recognition strategy with multi-timeframe analysis. Consistently achieves 85%+ win rate on V-75.',
      category: 'digit',
      tags: ['V-75', 'High Win Rate', 'AI-Assisted'],
      rating: 4.9,
      reviews: 234,
      downloads: 1250,
      winRate: 87,
      sharpeRatio: 2.4,
      maxDrawdown: 3.2,
      version: '2.1.0',
      lastUpdated: '2026-07-15',
      price: 0,
      verified: true,
      featured: true,
    },
    {
      id: '2',
      name: 'Trend Rider',
      author: 'AlgoTrader',
      authorAvatar: 'A',
      description: 'Momentum-based trend following strategy for volatile markets. Adapts to different market regimes automatically.',
      category: 'trend',
      tags: ['V-50', 'Trend', 'Adaptive'],
      rating: 4.7,
      reviews: 156,
      downloads: 890,
      winRate: 78,
      sharpeRatio: 1.9,
      maxDrawdown: 5.1,
      version: '1.5.2',
      lastUpdated: '2026-07-10',
      price: 29,
      verified: true,
      featured: false,
    },
    {
      id: '3',
      name: 'Grid Pro 75',
      author: 'GridMaster',
      authorAvatar: 'G',
      description: 'Sophisticated grid trading system with dynamic lot sizing. Ideal for range-bound markets.',
      category: 'grid',
      tags: ['V-75', 'Grid', 'Low Risk'],
      rating: 4.5,
      reviews: 89,
      downloads: 567,
      winRate: 72,
      sharpeRatio: 1.6,
      maxDrawdown: 4.8,
      version: '3.0.1',
      lastUpdated: '2026-07-12',
      price: 49,
      verified: true,
      featured: false,
    },
    {
      id: '4',
      name: 'Breakout Hunter',
      author: 'VolatilityKing',
      authorAvatar: 'V',
      description: 'Captures explosive breakouts using advanced volatility analysis. Best during high-volatility sessions.',
      category: 'breakout',
      tags: ['V-25', 'Breakout', 'High Risk'],
      rating: 4.3,
      reviews: 67,
      downloads: 345,
      winRate: 65,
      sharpeRatio: 1.4,
      maxDrawdown: 8.2,
      version: '1.2.0',
      lastUpdated: '2026-06-28',
      price: 39,
      verified: false,
      featured: false,
    },
    {
      id: '5',
      name: 'Mean Reversion Elite',
      author: 'StatsGuru',
      authorAvatar: 'S',
      description: 'Statistical arbitrage strategy that exploits mean reversion patterns. Consistent returns with controlled risk.',
      category: 'mean-reversion',
      tags: ['V-50', 'Statistical', 'Conservative'],
      rating: 4.8,
      reviews: 178,
      downloads: 920,
      winRate: 82,
      sharpeRatio: 2.1,
      maxDrawdown: 4.1,
      version: '2.3.0',
      lastUpdated: '2026-07-14',
      price: 19,
      verified: true,
      featured: false,
    },
  ];

  const filteredStrategies = strategies
    .filter(s => selectedCategory === 'all' || s.category === selectedCategory)
    .filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                  s.description.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'rating') return b.rating - a.rating;
      if (sortBy === 'downloads') return b.downloads - a.downloads;
      return new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime();
    });

  const toggleFavorite = (id: string) => {
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleImport = (strategy: Strategy) => {
    alert(`Importing ${strategy.name}...`);
  };

  const handleDuplicate = (strategy: Strategy) => {
    alert(`Creating copy of ${strategy.name}...`);
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">Strategy Marketplace</h1>
          <p className="text-slate-400">Discover, import, and share trading strategies with the community</p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="relative flex-1 min-w-64">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search strategies..."
              className="w-full pl-12 pr-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.label}</option>
            ))}
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="rating">Top Rated</option>
            <option value="downloads">Most Downloads</option>
            <option value="newest">Recently Updated</option>
          </select>

          <button className="flex items-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition-colors">
            <Upload className="w-4 h-4" />
            Upload Strategy
          </button>
        </div>

        {/* Categories */}
        <div className="flex flex-wrap gap-2 mb-6">
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Strategy Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredStrategies.map(strategy => (
            <div
              key={strategy.id}
              className={`bg-slate-900 rounded-xl border overflow-hidden transition-all hover:border-slate-700 ${
                strategy.featured ? 'border-blue-500/50 ring-2 ring-blue-500/20' : 'border-slate-800'
              }`}
            >
              {strategy.featured && (
                <div className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs font-medium">
                  Featured Strategy
                </div>
              )}

              <div className="p-5">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                      {strategy.authorAvatar}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-white">{strategy.name}</h3>
                        {strategy.verified && (
                          <CheckCircle2 className="w-4 h-4 text-blue-400" />
                        )}
                      </div>
                      <p className="text-xs text-slate-500">by {strategy.author}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleFavorite(strategy.id)}
                    className="p-2 text-slate-500 hover:text-red-400 transition-colors"
                  >
                    <Heart className={`w-5 h-5 ${favorites.has(strategy.id) ? 'fill-red-400 text-red-400' : ''}`} />
                  </button>
                </div>

                {/* Description */}
                <p className="text-sm text-slate-400 mb-4 line-clamp-2">{strategy.description}</p>

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {strategy.tags.map(tag => (
                    <span key={tag} className="px-2 py-1 bg-slate-800 text-slate-400 text-xs rounded-full flex items-center gap-1">
                      <Tag className="w-3 h-3" />
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                    <div className="flex items-center justify-center gap-1 text-emerald-400 mb-1">
                      <TrendingUp className="w-3 h-3" />
                      <span className="text-sm font-bold">{strategy.winRate}%</span>
                    </div>
                    <p className="text-xs text-slate-500">Win Rate</p>
                  </div>
                  <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                    <p className="text-sm font-bold text-white mb-1">{strategy.sharpeRatio}</p>
                    <p className="text-xs text-slate-500">Sharpe</p>
                  </div>
                  <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                    <p className="text-sm font-bold text-amber-400 mb-1">{strategy.maxDrawdown}%</p>
                    <p className="text-xs text-slate-500">Max DD</p>
                  </div>
                </div>

                {/* Meta */}
                <div className="flex items-center justify-between text-xs text-slate-500 mb-4">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                      {strategy.rating}
                    </div>
                    <div className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {strategy.downloads}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <GitBranch className="w-3 h-3" />
                    v{strategy.version}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleImport(strategy)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    {strategy.price === 0 ? 'Free' : `$${strategy.price}`}
                  </button>
                  <button
                    onClick={() => handleDuplicate(strategy)}
                    className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition-colors"
                    title="Duplicate"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition-colors"
                    title="Share"
                  >
                    <Share2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredStrategies.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            <Search className="w-12 h-12 mx-auto mb-4 text-slate-600" />
            <p>No strategies found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
