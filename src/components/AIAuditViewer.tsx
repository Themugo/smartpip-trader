import { useState, useEffect } from 'react';

interface Explanation {
  explanation_id: string;
  decision_id: string;
  timestamp: string;
  action: string;
  symbol: string;
  confidence: number;
  risk_level: string;
  expected_value: number;
  summary: string;
}

interface EvidenceItem {
  type: string;
  timestamp: string;
  weight: number;
  data: Record<string, any>;
}

interface AuditReport {
  report_id: string;
  generated_at: string;
  explanation_id: string;
  decision_id: string;
  integrity_check: Record<string, boolean>;
  completeness_score: number;
  decision_validity: string;
  confidence_validity: string;
  risk_assessment_validity: string;
  findings: string[];
  recommendations: string[];
}

interface Reconstruction {
  explanation_id: string;
  decision_id: string;
  timestamp: string;
  original_action: string;
  original_confidence: number;
  original_expected_value: number;
  evidence_chain: EvidenceItem[];
  analyzer_signals: Record<string, any>;
  decision_tree: { step: number; description: string; type: string }[];
  alternatives: any[];
  rejection_reasons: string[];
  feature_importance: Record<string, number>;
  historical_analogues: any[];
  market_conditions: Record<string, any>;
  integrity_verified: boolean;
  reconstruction_notes: string[];
}

type TabLevel = 'beginner' | 'advanced' | 'developer' | 'researcher';

export default function AIAuditViewer() {
  const [explanations, setExplanations] = useState<Explanation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fullExplanation, setFullExplanation] = useState<any>(null);
  const [auditReport, setAuditReport] = useState<AuditReport | null>(null);
  const [reconstruction, setReconstruction] = useState<Reconstruction | null>(null);
  const [activeTab, setActiveTab] = useState<TabLevel>('beginner');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'detail' | 'audit'>('list');

  useEffect(() => {
    fetchRecentExplanations();
  }, []);

  const fetchRecentExplanations = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/explainability/recent?limit=20');
      const data = await response.json();
      if (data.success) {
        setExplanations(data.explanations);
      }
    } catch (error) {
      console.error('Error fetching explanations:', error);
    } finally {
      setLoading(false);
    }
  };

  const searchExplanations = async () => {
    if (!searchQuery.trim()) {
      fetchRecentExplanations();
      return;
    }
    try {
      setLoading(true);
      const response = await fetch(`/api/explainability/search?q=${encodeURIComponent(searchQuery)}`);
      const data = await response.json();
      if (data.success) {
        setExplanations(data.results.map((r: any) => ({
          explanation_id: r.explanation_id,
          decision_id: r.decision_id,
          timestamp: r.timestamp,
          action: r.action,
          symbol: r.symbol,
          confidence: r.confidence,
          risk_level: r.risk_level,
          expected_value: r.expected_value,
          summary: r.summary,
        })));
      }
    } catch (error) {
      console.error('Error searching explanations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchExplanation = async (id: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/explainability/explanation/${id}`);
      const data = await response.json();
      if (data.success) {
        setFullExplanation(data.explanation);
        setSelectedId(id);
        setViewMode('detail');
      }
    } catch (error) {
      console.error('Error fetching explanation:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditReport = async (id: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/explainability/audit/${id}`);
      const data = await response.json();
      if (data.success) {
        setAuditReport(data.report);
        setViewMode('audit');
      }
    } catch (error) {
      console.error('Error fetching audit report:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReconstruction = async (id: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/explainability/reconstruct/${id}`);
      const data = await response.json();
      if (data.success) {
        setReconstruction(data.reconstruction);
      }
    } catch (error) {
      console.error('Error fetching reconstruction:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExplanation = (id: string) => {
    fetchExplanation(id);
    fetchAuditReport(id);
    fetchReconstruction(id);
  };

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'bg-green-100 text-green-800';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
      case 'HIGH': return 'bg-red-100 text-red-800';
      case 'CRITICAL': return 'bg-red-600 text-white';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getValidityBadge = (validity: string) => {
    switch (validity) {
      case 'VALID': return 'bg-green-500 text-white';
      case 'INVALID': return 'bg-red-500 text-white';
      case 'UNCERTAIN': return 'bg-yellow-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const renderBeginnerExplanation = () => {
    if (!fullExplanation?.beginner) return <p>No beginner explanation available.</p>;
    const b = fullExplanation.beginner;
    return (
      <div className="space-y-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">What Happened</h3>
          <p>{b.what_happened || 'N/A'}</p>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Why This Decision</h3>
          <p>{b.why || 'N/A'}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">How Confident</h3>
          <p>{b.how_confident || 'N/A'}</p>
        </div>
        <div className="bg-orange-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">How Risky</h3>
          <p>{b.how_risky || 'N/A'}</p>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Recommendation</h3>
          <p>{b.recommendation || 'N/A'}</p>
        </div>
      </div>
    );
  };

  const renderAdvancedExplanation = () => {
    if (!fullExplanation?.advanced) return <p>No advanced explanation available.</p>;
    const a = fullExplanation.advanced;
    return (
      <div className="space-y-4">
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Market Context</h3>
          <div className="grid grid-cols-2 gap-2">
            <p><strong>Regime:</strong> {a.market_context?.regime || 'N/A'}</p>
            <p><strong>Volatility:</strong> {a.market_context?.volatility || 0}</p>
            <p><strong>Balance:</strong> ${a.market_context?.balance || 0}</p>
            <p><strong>Exposure:</strong> {a.market_context?.exposure || 0}%</p>
          </div>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Signal Breakdown</h3>
          <div className="space-y-2">
            {a.signal_breakdown?.map((signal: any, i: number) => (
              <div key={i} className="flex justify-between items-center">
                <span className="font-medium">{signal.analyzer}</span>
                <span>{signal.signal} ({signal.confidence}%)</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Risk Metrics</h3>
          <div className="grid grid-cols-2 gap-2">
            <p><strong>Risk Score:</strong> {a.risk_metrics?.risk_score || 0}</p>
            <p><strong>Risk Level:</strong> <span className={`px-2 py-1 rounded text-sm ${getRiskBadgeColor(a.risk_metrics?.risk_level)}`}>{a.risk_metrics?.risk_level}</span></p>
            <p><strong>Uncertainty:</strong> {a.risk_metrics?.uncertainty || 0}</p>
            <p><strong>Calibration:</strong> {a.risk_metrics?.calibration_confidence || 0}%</p>
          </div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Trade Management</h3>
          <p><strong>Entry:</strong> {a.trade_management?.entry_strategy?.type || 'N/A'}</p>
          <p><strong>Exit:</strong> {a.trade_management?.exit_strategy?.time_based || 'N/A'}</p>
        </div>
      </div>
    );
  };

  const renderDeveloperExplanation = () => {
    if (!fullExplanation?.developer) return <p>No developer explanation available.</p>;
    const d = fullExplanation.developer;
    return (
      <div className="space-y-4">
        <div className="bg-gray-800 text-gray-100 p-4 rounded-lg font-mono text-sm">
          <h3 className="font-semibold text-lg mb-2">System Information</h3>
          <pre>{JSON.stringify(d.system_info, null, 2)}</pre>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Analyzers Used</h3>
          <div className="flex flex-wrap gap-2">
            {d.analyzers_used?.map((a: string, i: number) => (
              <span key={i} className="bg-blue-200 px-2 py-1 rounded text-sm">{a}</span>
            ))}
          </div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Feature Importance</h3>
          <div className="space-y-1">
            {d.top_features?.slice(0, 10).map(([feature, importance]: [string, number], i: number) => (
              <div key={i} className="flex justify-between">
                <code className="text-sm">{feature}</code>
                <span>{importance.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Implementation</h3>
          <pre className="text-sm overflow-x-auto">{JSON.stringify(d.implementation, null, 2)}</pre>
        </div>
      </div>
    );
  };

  const renderResearcherExplanation = () => {
    if (!fullExplanation?.researcher) return <p>No researcher explanation available.</p>;
    const r = fullExplanation.researcher;
    return (
      <div className="space-y-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Methodology</h3>
          <p><strong>Approach:</strong> {r.methodology?.approach || 'N/A'}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Statistical Analysis</h3>
          <div className="grid grid-cols-2 gap-2">
            <p><strong>Confidence:</strong> {r.statistics?.confidence?.value || 0}</p>
            <p><strong>Calibration:</strong> {r.statistics?.confidence?.calibration_confidence || 0}</p>
            <p><strong>Uncertainty:</strong> {r.statistics?.confidence?.uncertainty_estimate || 0}</p>
            <p><strong>Std Error:</strong> {r.statistics?.confidence?.standard_error || 0}</p>
          </div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Probability Analysis</h3>
          <div className="grid grid-cols-2 gap-2">
            <p><strong>Expected Value:</strong> {r.probability_analysis?.expected_value || 0}</p>
            <p><strong>Variance:</strong> {r.probability_analysis?.variance || 0}</p>
            <p><strong>Sharpe Ratio:</strong> {r.probability_analysis?.sharpe_ratio || 0}</p>
          </div>
        </div>
        <div className="bg-yellow-50 p-4 rounded-lg">
          <h3 className="font-semibold text-lg mb-2">Evidence Weights</h3>
          <div className="space-y-1">
            {Object.entries(r.evidence_weights || {}).map(([type, weight], i) => (
              <div key={i} className="flex justify-between">
                <span className="capitalize">{type.replace('_', ' ')}</span>
                <span>{Number(weight).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderEvidenceChain = () => {
    const evidence = fullExplanation?.evidence_chain || [];
    if (evidence.length === 0) return <p>No evidence available.</p>;
    
    return (
      <div className="space-y-4">
        {evidence.map((item: EvidenceItem, i: number) => (
          <div key={i} className="border-l-4 border-blue-500 pl-4">
            <div className="flex justify-between items-start">
              <h4 className="font-semibold capitalize">{item.type.replace('_', ' ')}</h4>
              <span className="text-sm text-gray-500">Weight: {item.weight.toFixed(2)}</span>
            </div>
            <pre className="text-xs bg-gray-50 p-2 rounded mt-2 overflow-x-auto">
              {JSON.stringify(item.data, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">AI Audit Viewer</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 rounded ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            List
          </button>
          <button
            onClick={() => setViewMode('detail')}
            className={`px-4 py-2 rounded ${viewMode === 'detail' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            disabled={!selectedId}
          >
            Detail
          </button>
          <button
            onClick={() => setViewMode('audit')}
            className={`px-4 py-2 rounded ${viewMode === 'audit' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            disabled={!selectedId}
          >
            Audit
          </button>
        </div>
      </div>

      {viewMode === 'list' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchExplanations()}
              placeholder="Search explanations..."
              className="flex-1 px-4 py-2 border rounded-lg"
            />
            <button
              onClick={searchExplanations}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg"
            >
              Search
            </button>
          </div>

          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {explanations.map((exp) => (
                    <tr
                      key={exp.explanation_id}
                      onClick={() => handleSelectExplanation(exp.explanation_id)}
                      className="hover:bg-gray-50 cursor-pointer"
                    >
                      <td className="px-6 py-4">
                        <span className="font-medium">{exp.action}</span>
                      </td>
                      <td className="px-6 py-4">{exp.symbol}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${exp.confidence}%` }}
                            />
                          </div>
                          <span>{exp.confidence}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs ${getRiskBadgeColor(exp.risk_level)}`}>
                          {exp.risk_level}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {new Date(exp.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {viewMode === 'detail' && fullExplanation && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold">Decision Explanation</h2>
                <p className="text-gray-500 text-sm">
                  {fullExplanation.executive_summary?.summary}
                </p>
              </div>
              <div className="flex gap-2">
                <span className={`px-3 py-1 rounded ${getRiskBadgeColor(fullExplanation.executive_summary?.risk_level)}`}>
                  {fullExplanation.executive_summary?.risk_level} RISK
                </span>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Confidence</p>
                <p className="text-2xl font-bold">{fullExplanation.executive_summary?.confidence}%</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Expected Value</p>
                <p className="text-2xl font-bold">{fullExplanation.executive_summary?.expected_value?.toFixed(4)}</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Why Opportunity</p>
                <p className="text-sm truncate">{fullExplanation.executive_summary?.why_opportunity_exists}</p>
              </div>
              <div className="bg-orange-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Why Confidence</p>
                <p className="text-sm truncate">{fullExplanation.executive_summary?.why_confidence_level}</p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg">
            <div className="border-b">
              <div className="flex">
                {(['beginner', 'advanced', 'developer', 'researcher'] as TabLevel[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-6 py-3 font-medium capitalize ${
                      activeTab === tab
                        ? 'border-b-2 border-blue-600 text-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>
            <div className="p-6">
              {activeTab === 'beginner' && renderBeginnerExplanation()}
              {activeTab === 'advanced' && renderAdvancedExplanation()}
              {activeTab === 'developer' && renderDeveloperExplanation()}
              {activeTab === 'researcher' && renderResearcherExplanation()}
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Evidence Chain</h3>
            {renderEvidenceChain()}
          </div>
        </div>
      )}

      {viewMode === 'audit' && auditReport && reconstruction && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold">Audit Report</h2>
                <p className="text-gray-500">Report ID: {auditReport.report_id}</p>
              </div>
              <span className={`px-3 py-1 rounded ${getValidityBadge(auditReport.decision_validity)}`}>
                {auditReport.decision_validity}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Decision Validity</p>
                <span className={`px-2 py-1 rounded text-sm ${getValidityBadge(auditReport.decision_validity)}`}>
                  {auditReport.decision_validity}
                </span>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Confidence Validity</p>
                <span className={`px-2 py-1 rounded text-sm ${getValidityBadge(auditReport.confidence_validity)}`}>
                  {auditReport.confidence_validity}
                </span>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Risk Validity</p>
                <span className={`px-2 py-1 rounded text-sm ${getValidityBadge(auditReport.risk_assessment_validity)}`}>
                  {auditReport.risk_assessment_validity}
                </span>
              </div>
            </div>

            <div className="mb-6">
              <h3 className="font-semibold mb-2">Completeness Score</h3>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className="bg-blue-600 h-4 rounded-full"
                  style={{ width: `${auditReport.completeness_score * 100}%` }}
                />
              </div>
              <p className="text-right text-sm mt-1">{(auditReport.completeness_score * 100).toFixed(0)}%</p>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Integrity Checks</h3>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(auditReport.integrity_check).map(([check, passed]) => (
                <div key={check} className="flex items-center gap-2">
                  {passed ? (
                    <span className="text-green-500">✓</span>
                  ) : (
                    <span className="text-red-500">✗</span>
                  )}
                  <span className="capitalize">{check.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Findings</h3>
            <ul className="space-y-2">
              {auditReport.findings.map((finding, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
            <ul className="space-y-2">
              {auditReport.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-yellow-500">⚠</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Decision Reconstruction</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-500">Original Action</p>
                <p className="font-medium">{reconstruction.original_action}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Original Confidence</p>
                <p className="font-medium">{reconstruction.original_confidence}%</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Expected Value</p>
                <p className="font-medium">{reconstruction.original_expected_value}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Integrity Verified</p>
                <p className="font-medium">{reconstruction.integrity_verified ? 'Yes' : 'No'}</p>
              </div>
            </div>

            {reconstruction.reconstruction_notes.length > 0 && (
              <div className="mt-4">
                <h4 className="font-medium mb-2">Reconstruction Notes</h4>
                <ul className="space-y-1 text-sm text-gray-600">
                  {reconstruction.reconstruction_notes.map((note, i) => (
                    <li key={i}>• {note}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4">
              <h4 className="font-medium mb-2">Decision Tree ({reconstruction.decision_tree.length} steps)</h4>
              <div className="space-y-2">
                {reconstruction.decision_tree.map((step, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className="bg-gray-200 px-2 py-1 rounded text-xs">{i + 1}</span>
                    <span>{step.description}</span>
                    <span className="text-gray-500 text-xs">({step.type})</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
