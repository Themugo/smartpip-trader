import { useState, useRef, useEffect } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  FastForward,
  Rewind,
  Bookmark,
  MessageSquare,
  Download,
  Maximize2,
  Volume2,
  BarChart3,
  Clock,
  TrendingUp,
  TrendingDown,
  Brain,
  ChevronLeft,

  Flag,
  Share2,
  Filter
} from 'lucide-react';

interface TradeAnnotation {
  id: string;
  time: number;
  type: 'ai_commentary' | 'market_event' | 'trade_marker' | 'pattern' | 'custom' | 'trade_entry' | 'trade_exit' | 'regime_change';
  content: string;
  important: boolean;
}

export function ReplayIntelligence() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(3600); // 1 hour in seconds
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [volume, setVolume] = useState(80);
  const [bookmarks, setBookmarks] = useState<{ time: number; label: string }[]>([
    { time: 300, label: 'First trade' },
    { time: 1200, label: 'High volatility' },
    { time: 2400, label: 'Strategy change' },
  ]);
  const [annotations, setAnnotations] = useState<TradeAnnotation[]>([
    { id: '1', time: 450, type: 'ai_commentary', content: 'Strong buy signal detected. Pattern match at 94% confidence.', important: true },
    { id: '2', time: 900, type: 'trade_entry', content: 'Bought V-75 UP at 1845.32', important: true },
    { id: '3', time: 1350, type: 'trade_exit', content: 'Trade closed +$85.50 (4.2% profit)', important: false },
    { id: '4', time: 1800, type: 'pattern', content: 'Double top pattern forming. Consider closing positions.', important: true },
    { id: '5', time: 2100, type: 'regime_change', content: 'Market regime shifted from trending to ranging.', important: true },
  ]);
  const [showAnnotations, setShowAnnotations] = useState(true);
  const [selectedBookmark, setSelectedBookmark] = useState<number | null>(null);
  const [comparisonMode, setComparisonMode] = useState(false);
  const videoRef = useRef<HTMLDivElement>(null);

  // Simulate playback
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime(prev => {
          if (prev >= duration) {
            setIsPlaying(false);
            return duration;
          }
          return prev + playbackSpeed;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, duration]);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    setCurrentTime(Math.floor(percent * duration));
  };

  const addBookmark = () => {
    const label = prompt('Enter bookmark label:');
    if (label) {
      setBookmarks(prev => [...prev, { time: currentTime, label }].sort((a, b) => a.time - b.time));
    }
  };

  const getAnnotationIcon = (type: TradeAnnotation['type']) => {
    switch (type) {
      case 'ai_commentary':
        return <Brain className="w-4 h-4 text-blue-400" />;
      case 'trade_entry':
        return <TrendingUp className="w-4 h-4 text-emerald-400" />;
      case 'trade_exit':
        return <TrendingDown className="w-4 h-4 text-amber-400" />;
      case 'pattern':
        return <BarChart3 className="w-4 h-4 text-purple-400" />;
      case 'market_event':
        return <Flag className="w-4 h-4 text-red-400" />;
      default:
        return <MessageSquare className="w-4 h-4 text-slate-400" />;
    }
  };

  const visibleAnnotations = annotations.filter(a => 
    Math.abs(a.time - currentTime) < 60 || showAnnotations
  );

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <button className="p-2 text-slate-400 hover:text-white">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">Replay: V-75 Trading Session</h1>
            <p className="text-sm text-slate-500">July 15, 2026 • 2:00 PM - 3:00 PM</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setComparisonMode(!comparisonMode)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              comparisonMode
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Comparison Mode
          </button>
          <button className="p-2 bg-slate-800 text-slate-400 hover:text-white rounded-lg">
            <Download className="w-5 h-5" />
          </button>
          <button className="p-2 bg-slate-800 text-slate-400 hover:text-white rounded-lg">
            <Share2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Main Replay Area */}
        <div className="flex-1 flex flex-col">
          {/* Video/Chart Area */}
          <div ref={videoRef} className="flex-1 bg-slate-900/50 relative">
            {/* Simulated Chart */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-full h-full p-8">
                <div className="bg-slate-800/50 rounded-xl h-full flex items-center justify-center relative overflow-hidden">
                  {/* Simulated price chart */}
                  <svg className="w-full h-full" preserveAspectRatio="none">
                    <path
                      d={`M 0 ${300 + Math.sin(0) * 50} ${Array.from({ length: 100 }, (_, i) => {
                        const x = (i / 100) * 100;
                        const y = 300 + Math.sin(i * 0.1 + currentTime * 0.01) * 100 + Math.sin(i * 0.05) * 50;
                        return `L ${x}% ${y}`;
                      }).join(' ')}`}
                      fill="none"
                      stroke="#3B82F6"
                      strokeWidth="2"
                      className="transition-all duration-100"
                    />
                    {/* Current position marker */}
                    <circle
                      cx={`${(currentTime / duration) * 100}%`}
                      cy="300"
                      r="6"
                      fill="#3B82F6"
                      className="animate-pulse"
                    />
                  </svg>
                  
                  {/* Time indicator */}
                  <div 
                    className="absolute top-0 bottom-0 w-0.5 bg-blue-500 transition-all duration-100"
                    style={{ left: `${(currentTime / duration) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* AI Commentary Overlay */}
            {showAnnotations && currentTime > 0 && annotations
              .filter(a => Math.abs(a.time - currentTime) < 30)
              .map(ann => (
                <div
                  key={ann.id}
                  className={`absolute left-4 top-4 max-w-sm p-4 rounded-xl border ${
                    ann.important
                      ? 'bg-blue-500/20 border-blue-500/50'
                      : 'bg-slate-800/80 border-slate-700'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {getAnnotationIcon(ann.type)}
                    <div>
                      <p className="text-sm text-white">{ann.content}</p>
                      <p className="text-xs text-slate-500 mt-1">{formatTime(ann.time)}</p>
                    </div>
                  </div>
                </div>
              ))
            }
          </div>

          {/* Timeline Controls */}
          <div className="bg-slate-900 border-t border-slate-800 p-4">
            {/* Progress Bar */}
            <div className="relative h-2 bg-slate-800 rounded-full mb-4 cursor-pointer group" onClick={handleSeek}>
              <div
                className="absolute h-full bg-blue-600 rounded-full"
                style={{ width: `${(currentTime / duration) * 100}%` }}
              />
              <div
                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-blue-500 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ left: `calc(${(currentTime / duration) * 100}% - 8px)` }}
              />
              
              {/* Bookmarks on timeline */}
              {bookmarks.map((bookmark, i) => (
                <button
                  key={i}
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentTime(bookmark.time);
                  }}
                  className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-yellow-500 rounded-full hover:scale-125 transition-transform"
                  style={{ left: `calc(${(bookmark.time / duration) * 100}% - 6px)` }}
                  title={bookmark.label}
                />
              ))}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentTime(0)}
                  className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                  <SkipBack className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setCurrentTime(Math.max(0, currentTime - 60))}
                  className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                  <Rewind className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="p-3 bg-blue-600 hover:bg-blue-500 text-white rounded-full transition-colors"
                >
                  {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                </button>
                <button
                  onClick={() => setCurrentTime(Math.min(duration, currentTime + 60))}
                  className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                  <FastForward className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setCurrentTime(duration)}
                  className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                  <SkipForward className="w-5 h-5" />
                </button>
              </div>

              <div className="flex items-center gap-4">
                <span className="text-sm text-white font-mono">{formatTime(currentTime)}</span>
                <span className="text-slate-500">/</span>
                <span className="text-sm text-slate-400 font-mono">{formatTime(duration)}</span>
              </div>

              <div className="flex items-center gap-4">
                {/* Playback Speed */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Speed:</span>
                  {[0.5, 1, 2, 4].map(speed => (
                    <button
                      key={speed}
                      onClick={() => setPlaybackSpeed(speed)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        playbackSpeed === speed
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      {speed}x
                    </button>
                  ))}
                </div>

                {/* Volume */}
                <div className="flex items-center gap-2">
                  <Volume2 className="w-4 h-4 text-slate-400" />
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={volume}
                    onChange={(e) => setVolume(Number(e.target.value))}
                    className="w-20 accent-blue-500"
                  />
                </div>

                {/* Bookmark */}
                <button
                  onClick={addBookmark}
                  className="p-2 text-slate-400 hover:text-yellow-400 transition-colors"
                  title="Add Bookmark"
                >
                  <Bookmark className="w-5 h-5" />
                </button>

                {/* Toggle Annotations */}
                <button
                  onClick={() => setShowAnnotations(!showAnnotations)}
                  className={`p-2 transition-colors ${showAnnotations ? 'text-blue-400' : 'text-slate-400 hover:text-white'}`}
                  title="Toggle AI Commentary"
                >
                  <Brain className="w-5 h-5" />
                </button>

                {/* Fullscreen */}
                <button className="p-2 text-slate-400 hover:text-white transition-colors">
                  <Maximize2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar - Annotations & Bookmarks */}
        <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col">
          {/* Bookmarks */}
          <div className="p-4 border-b border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-white flex items-center gap-2">
                <Bookmark className="w-4 h-4 text-yellow-400" />
                Bookmarks
              </h3>
              <span className="text-xs text-slate-500">{bookmarks.length}</span>
            </div>
            <div className="space-y-2">
              {bookmarks.map((bookmark, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentTime(bookmark.time)}
                  className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-colors ${
                    Math.abs(currentTime - bookmark.time) < 5
                      ? 'bg-blue-500/20 border border-blue-500/50'
                      : 'hover:bg-slate-800'
                  }`}
                >
                  <Clock className="w-4 h-4 text-slate-500" />
                  <span className="text-sm text-white">{bookmark.label}</span>
                  <span className="ml-auto text-xs text-slate-500">{formatTime(bookmark.time)}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Annotations Timeline */}
          <div className="flex-1 overflow-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-white flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-blue-400" />
                AI Commentary
              </h3>
              <button className="p-1 text-slate-500 hover:text-white">
                <Filter className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3">
              {annotations.sort((a, b) => a.time - b.time).map(annotation => (
                <button
                  key={annotation.id}
                  onClick={() => setCurrentTime(annotation.time)}
                  className={`w-full p-3 rounded-lg text-left transition-colors ${
                    Math.abs(currentTime - annotation.time) < 30
                      ? 'bg-blue-500/20 border border-blue-500/50'
                      : 'bg-slate-800/50 hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {getAnnotationIcon(annotation.type)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-slate-500">{formatTime(annotation.time)}</span>
                        {annotation.important && (
                          <Flag className="w-3 h-3 text-red-400" />
                        )}
                      </div>
                      <p className="text-sm text-slate-300 line-clamp-2">{annotation.content}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Export Report */}
          <div className="p-4 border-t border-slate-800">
            <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium text-sm transition-colors">
              <Download className="w-4 h-4" />
              Export Replay Report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
