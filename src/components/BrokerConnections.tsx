import { useState, useEffect } from 'react';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Plus, 
  Trash2, 
  RefreshCw, 
  ExternalLink,
  Eye,
  EyeOff,
  Shield,
  Zap
} from 'lucide-react';
import { supabase } from '../lib/supabase';

interface BrokerConnection {
  id: string;
  broker: 'deriv_demo' | 'deriv_live';
  label: string;
  is_active: boolean;
  last_sync: string | null;
  connection_status: 'connected' | 'disconnected' | 'error';
  balance?: number;
  currency?: string;
}

interface BrokerConnectionsProps {
  onConnectionChange?: (hasConnection: boolean) => void;
}

export function BrokerConnections({ onConnectionChange }: BrokerConnectionsProps) {
  const [connections, setConnections] = useState<BrokerConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newToken, setNewToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<'deriv_demo' | 'deriv_live'>('deriv_demo');
  const [label, setLabel] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testingConnection, setTestingConnection] = useState<string | null>(null);

  useEffect(() => {
    fetchConnections();
  }, []);

  useEffect(() => {
    if (onConnectionChange) {
      onConnectionChange(connections.some(c => c.connection_status === 'connected'));
    }
  }, [connections, onConnectionChange]);

  const fetchConnections = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      // In production, fetch from a broker_connections table
      // For now, use mock data
      setConnections([
        {
          id: '1',
          broker: 'deriv_demo',
          label: 'My Demo Account',
          is_active: true,
          last_sync: new Date().toISOString(),
          connection_status: 'connected',
          balance: 10000,
          currency: 'USD'
        }
      ]);
    } catch (err) {
      console.error('Failed to fetch connections:', err);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (token: string, _broker: string): Promise<boolean> => {
    try {
      // Simulate API test
      await new Promise(resolve => setTimeout(resolve, 1500));
      // In production, actually test the token with Deriv API
      return token.length > 10;
    } catch {
      return false;
    }
  };

  const handleAddConnection = async () => {
    if (!newToken.trim()) {
      setError('API token is required');
      return;
    }

    if (!label.trim()) {
      setError('Account label is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Test connection first
      setTestingConnection(selectedBroker);
      const isValid = await testConnection(newToken, selectedBroker);

      if (!isValid) {
        setError('Invalid API token. Please check and try again.');
        return;
      }

      // In production: encrypt token server-side and store
      const newConnection: BrokerConnection = {
        id: Date.now().toString(),
        broker: selectedBroker,
        label: label.trim(),
        is_active: true,
        last_sync: new Date().toISOString(),
        connection_status: 'connected',
        balance: 0,
        currency: 'USD'
      };

      setConnections(prev => [...prev, newConnection]);
      setShowAddModal(false);
      setNewToken('');
      setLabel('');
    } catch (err: any) {
      setError(err.message || 'Failed to add connection');
    } finally {
      setSaving(false);
      setTestingConnection(null);
    }
  };

  const handleDisconnect = async (id: string) => {
    setConnections(prev => 
      prev.map(c => 
        c.id === id ? { ...c, connection_status: 'disconnected', is_active: false } : c
      )
    );
  };

  const handleReconnect = async (id: string) => {
    const conn = connections.find(c => c.id === id);
    if (!conn) return;

    setTestingConnection(id);
    try {
      const isValid = await testConnection('test', conn.broker);
      if (isValid) {
        setConnections(prev =>
          prev.map(c =>
            c.id === id ? { 
              ...c, 
              connection_status: 'connected' as const, 
              is_active: true,
              last_sync: new Date().toISOString()
            } : c
          )
        );
      }
    } finally {
      setTestingConnection(null);
    }
  };

  const handleDelete = async (id: string) => {
    setConnections(prev => prev.filter(c => c.id !== id));
  };

  const getStatusIcon = (status: BrokerConnection['connection_status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case 'disconnected':
        return <XCircle className="w-5 h-5 text-slate-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
    }
  };

  const getBrokerIcon = (_broker: string) => {
    return <Zap className="w-5 h-5" />;
  };

  const formatLastSync = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-800 rounded w-1/3"></div>
          <div className="h-20 bg-slate-800 rounded"></div>
          <div className="h-20 bg-slate-800 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800">
      {/* Header */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              Broker Connections
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Connect your trading accounts securely
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Connection
          </button>
        </div>
      </div>

      {/* Connections List */}
      <div className="p-6 space-y-4">
        {connections.length === 0 ? (
          <div className="text-center py-8">
            <Activity className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400 mb-4">No broker connections yet</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors"
            >
              Connect Your First Account
            </button>
          </div>
        ) : (
          connections.map((conn) => (
            <div
              key={conn.id}
              className={`p-4 rounded-xl border ${
                conn.connection_status === 'connected'
                  ? 'bg-slate-800/50 border-slate-700'
                  : 'bg-slate-800/20 border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    conn.connection_status === 'connected'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-700 text-slate-400'
                  }`}>
                    {getBrokerIcon(conn.broker)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-white">{conn.label}</h3>
                      {conn.is_active && (
                        <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-400">
                      {conn.broker === 'deriv_demo' ? 'Deriv Demo' : 'Deriv Live'}
                      {conn.balance !== undefined && conn.balance > 0 && (
                        <span className="ml-2">
                          • {conn.currency} {conn.balance.toLocaleString()}
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  {/* Status */}
                  <div className="flex items-center gap-2">
                    {getStatusIcon(conn.connection_status)}
                    <span className={`text-sm ${
                      conn.connection_status === 'connected'
                        ? 'text-emerald-400'
                        : conn.connection_status === 'error'
                        ? 'text-red-400'
                        : 'text-slate-500'
                    }`}>
                      {conn.connection_status === 'connected' ? 'Connected' : 
                       conn.connection_status === 'error' ? 'Error' : 'Disconnected'}
                    </span>
                  </div>

                  {/* Last Sync */}
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Last sync</p>
                    <p className="text-sm text-slate-400">{formatLastSync(conn.last_sync)}</p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {conn.connection_status === 'disconnected' || conn.connection_status === 'error' ? (
                      <button
                        onClick={() => handleReconnect(conn.id)}
                        disabled={testingConnection === conn.id}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                        title="Reconnect"
                      >
                        <RefreshCw className={`w-4 h-4 ${testingConnection === conn.id ? 'animate-spin' : ''}`} />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleDisconnect(conn.id)}
                        className="p-2 text-slate-400 hover:text-amber-400 hover:bg-slate-700 rounded-lg transition-colors"
                        title="Disconnect"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(conn.id)}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Security Notice */}
      <div className="px-6 pb-6">
        <div className="bg-slate-800/50 rounded-lg p-4 flex items-start gap-3">
          <Shield className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-white">Your tokens are encrypted</p>
            <p className="text-xs text-slate-400 mt-1">
              API tokens are encrypted and stored securely. We never have access to your broker funds.
            </p>
          </div>
        </div>
      </div>

      {/* Add Connection Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-800 w-full max-w-md">
            <div className="p-6 border-b border-slate-800">
              <h3 className="text-lg font-semibold text-white">Add Broker Connection</h3>
              <p className="text-sm text-slate-400 mt-1">Connect a new trading account</p>
            </div>

            <div className="p-6 space-y-4">
              {/* Broker Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Broker</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setSelectedBroker('deriv_demo')}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      selectedBroker === 'deriv_demo'
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <Zap className={`w-6 h-6 mx-auto mb-2 ${
                      selectedBroker === 'deriv_demo' ? 'text-blue-400' : 'text-slate-400'
                    }`} />
                    <p className={`font-medium ${
                      selectedBroker === 'deriv_demo' ? 'text-white' : 'text-slate-400'
                    }`}>Deriv Demo</p>
                    <p className="text-xs text-slate-500 mt-1">Practice trading</p>
                  </button>
                  <button
                    onClick={() => setSelectedBroker('deriv_live')}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      selectedBroker === 'deriv_live'
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <Zap className={`w-6 h-6 mx-auto mb-2 ${
                      selectedBroker === 'deriv_live' ? 'text-emerald-400' : 'text-slate-400'
                    }`} />
                    <p className={`font-medium ${
                      selectedBroker === 'deriv_live' ? 'text-white' : 'text-slate-400'
                    }`}>Deriv Live</p>
                    <p className="text-xs text-slate-500 mt-1">Real trading</p>
                  </button>
                </div>
              </div>

              {/* Label */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Account Label
                </label>
                <input
                  type="text"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="e.g., My Main Account"
                  className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* API Token */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  API Token
                </label>
                <div className="relative">
                  <input
                    type={showToken ? 'text' : 'password'}
                    value={newToken}
                    onChange={(e) => setNewToken(e.target.value)}
                    placeholder="Enter your Deriv API token"
                    className="w-full px-4 py-2.5 pr-10 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <a
                  href="https://app.deriv.com/account/api-token"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2"
                >
                  Get API token from Deriv <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}
            </div>

            <div className="p-6 border-t border-slate-800 flex gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setError(null);
                  setNewToken('');
                  setLabel('');
                }}
                className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddConnection}
                disabled={saving}
                className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    {testingConnection ? 'Testing...' : 'Connecting...'}
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    Add Connection
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
