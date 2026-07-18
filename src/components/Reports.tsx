/**
 * Professional Reporting
 * 
 * Generate and export professional reports in multiple formats.
 */

import { useState, type ReactNode } from 'react';
import { cn } from '../ui/utils';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Tabs } from '../ui/Tabs';

// Types
export type ReportType = 
  | 'daily-summary'
  | 'weekly-performance'
  | 'monthly-review'
  | 'risk-report'
  | 'portfolio-report'
  | 'replay-analysis'
  | 'strategy-comparison'
  | 'ai-decision-summary';

export type ExportFormat = 'pdf' | 'csv' | 'excel';

export interface ReportConfig {
  type: ReportType;
  dateRange?: { start: Date; end: Date };
  includeCharts?: boolean;
  includeAIInsights?: boolean;
  includeRiskMetrics?: boolean;
}

export interface ReportData {
  title: string;
  subtitle?: string;
  generatedAt: Date;
  sections: ReportSection[];
  metadata?: Record<string, unknown>;
}

export interface ReportSection {
  title: string;
  type: 'metrics' | 'table' | 'chart' | 'text' | 'divider';
  data?: Record<string, number | string>;
  columns?: { key: string; label: string; format?: string }[];
  rows?: Record<string, number | string | null>[];
  content?: string;
}

// Icons
const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const FileIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const ChartIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const TableIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

// Report Type Definitions
const REPORT_TYPES: { type: ReportType; label: string; description: string; icon: ReactNode }[] = [
  { type: 'daily-summary', label: 'Daily Summary', description: 'Trading activity for the day', icon: <FileIcon /> },
  { type: 'weekly-performance', label: 'Weekly Performance', description: '7-day performance review', icon: <ChartIcon /> },
  { type: 'monthly-review', label: 'Monthly Review', description: '30-day comprehensive review', icon: <ChartIcon /> },
  { type: 'risk-report', label: 'Risk Report', description: 'Risk metrics and analysis', icon: <ChartIcon /> },
  { type: 'portfolio-report', label: 'Portfolio Report', description: 'Portfolio holdings and allocation', icon: <TableIcon /> },
  { type: 'replay-analysis', label: 'Replay Analysis', description: 'Session replay insights', icon: <ChartIcon /> },
  { type: 'strategy-comparison', label: 'Strategy Comparison', description: 'Compare strategy performance', icon: <ChartIcon /> },
  { type: 'ai-decision-summary', label: 'AI Decision Summary', description: 'AI recommendations and outcomes', icon: <TableIcon /> },
];

// Format utilities
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

// Generate mock report data
function generateReportData(type: ReportType, dateRange?: { start: Date; end: Date }): ReportData {
  const now = new Date();
  const sections: ReportSection[] = [];

  switch (type) {
    case 'daily-summary':
      sections.push(
        {
          title: 'Performance Overview',
          type: 'metrics',
          data: {
            totalTrades: 24,
            winningTrades: 15,
            losingTrades: 9,
            winRate: 62.5,
            netProfit: 145.67,
            bestTrade: 35.50,
            worstTrade: -22.00,
            avgWin: 16.23,
            avgLoss: -11.45,
          },
        },
        {
          title: 'Trade History',
          type: 'table',
          columns: [
            { key: 'time', label: 'Time' },
            { key: 'market', label: 'Market' },
            { key: 'type', label: 'Type' },
            { key: 'direction', label: 'Direction' },
            { key: 'profit', label: 'Profit', format: 'currency' },
          ],
          rows: [
            { time: '09:30', market: 'R_100', type: 'DIGITOVER', direction: 'UP', profit: 15.50 },
            { time: '09:45', market: 'R_100', type: 'DIGITUNDER', direction: 'DOWN', profit: -12.00 },
            { time: '10:00', market: 'R_50', type: 'RISEFALL', direction: 'UP', profit: 25.00 },
          ],
        }
      );
      break;

    case 'weekly-performance':
      sections.push(
        {
          title: 'Weekly Statistics',
          type: 'metrics',
          data: {
            totalTrades: 142,
            winningTrades: 89,
            losingTrades: 53,
            winRate: 62.7,
            netProfit: 892.34,
            maxDrawdown: 8.5,
            profitFactor: 1.68,
          },
        },
        {
          title: 'Daily Breakdown',
          type: 'table',
          columns: [
            { key: 'date', label: 'Date' },
            { key: 'trades', label: 'Trades' },
            { key: 'winRate', label: 'Win Rate', format: 'percent' },
            { key: 'profit', label: 'Profit', format: 'currency' },
          ],
          rows: [
            { date: 'Mon', trades: 28, winRate: 64.3, profit: 156.78 },
            { date: 'Tue', trades: 32, winRate: 59.4, profit: 89.23 },
            { date: 'Wed', trades: 25, winRate: 68.0, profit: 234.56 },
            { date: 'Thu', trades: 30, winRate: 60.0, profit: -45.67 },
            { date: 'Fri', trades: 27, winRate: 66.7, profit: 457.44 },
          ],
        }
      );
      break;

    case 'risk-report':
      sections.push(
        {
          title: 'Risk Metrics',
          type: 'metrics',
          data: {
            riskScore: 68,
            maxDrawdown: 8.5,
            sharpeRatio: 1.23,
            volatility: 12.4,
            exposure: 45,
            correlation: 0.35,
          },
        },
        {
          title: 'Risk Factors',
          type: 'text',
          content: 'Current risk level is MODERATE. Drawdown is within acceptable limits. Consider reducing position sizes during high volatility periods.',
        }
      );
      break;

    default:
      sections.push({
        title: 'Summary',
        type: 'text',
        content: 'Report data for ' + type,
      });
  }

  return {
    title: REPORT_TYPES.find(r => r.type === type)?.label || type,
    subtitle: dateRange ? `${dateRange.start.toLocaleDateString()} - ${dateRange.end.toLocaleDateString()}` : undefined,
    generatedAt: now,
    sections,
    metadata: { reportType: type },
  };
}

// Export functions
function exportToCSV(report: ReportData): string {
  let csv = '';
  
  // Header
  csv += `"${report.title}"\n`;
  if (report.subtitle) csv += `"${report.subtitle}"\n`;
  csv += `"Generated: ${report.generatedAt.toISOString()}"\n\n`;
  
  // Sections
  report.sections.forEach(section => {
    csv += `"${section.title}"\n`;
    
    if (section.type === 'table' && section.columns && section.rows) {
      // Headers
      csv += section.columns.map(c => `"${c.label}"`).join(',') + '\n';
      
      // Rows
      section.rows.forEach(row => {
        const values = section.columns!.map(col => {
          const value = row[col.key];
          if (typeof value === 'number') {
            return col.format === 'currency' ? formatCurrency(value) : 
                   col.format === 'percent' ? formatPercent(value) : value.toString();
          }
          return `"${value ?? ''}"`;
        });
        csv += values.join(',') + '\n';
      });
    } else if (section.type === 'metrics' && section.data) {
      Object.entries(section.data as Record<string, unknown>).forEach(([key, value]) => {
        const displayValue = typeof value === 'number' ? value.toFixed(2) : value;
        csv += `"${key}","${displayValue}"\n`;
      });
    } else if (section.type === 'text' && section.content) {
      csv += `"${section.content.replace(/"/g, '""')}"\n`;
    }
    
    csv += '\n';
  });
  
  return csv;
}

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// Report Preview Component
function ReportPreview({ report }: { report: ReportData }) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center border-b border-slate-800 pb-6">
        <h1 className="text-2xl font-bold text-white">{report.title}</h1>
        {report.subtitle && <p className="text-slate-400 mt-1">{report.subtitle}</p>}
        <p className="text-sm text-slate-500 mt-2">
          Generated: {report.generatedAt.toLocaleString()}
        </p>
      </div>

      {/* Sections */}
      {report.sections.map((section, index) => (
        <div key={index} className="space-y-4">
          <h2 className="text-lg font-semibold text-white border-b border-slate-800 pb-2">
            {section.title}
          </h2>

          {section.type === 'metrics' && section.data && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(section.data as Record<string, number | string>).map(([key, value]) => (
                <div key={key} className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-400 uppercase">{key.replace(/([A-Z])/g, ' $1').trim()}</p>
                  <p className="text-xl font-semibold text-white mt-1">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {section.type === 'table' && section.columns && section.rows && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    {section.columns.map(col => (
                      <th key={col.key} className="text-left py-2 px-3 text-slate-400 font-medium">
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {section.rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="border-b border-slate-800 hover:bg-slate-800/30">
                      {section.columns!.map(col => {
                        const value = row[col.key];
                        let displayValue: string = String(value ?? '');
                        if (typeof value === 'number') {
                          if (col.format === 'currency') displayValue = formatCurrency(value);
                          else if (col.format === 'percent') displayValue = formatPercent(value);
                          else displayValue = String(value);
                        }
                        return (
                          <td key={col.key} className="py-2 px-3 text-slate-300">
                            {displayValue}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {section.type === 'text' && section.content && (
            <p className="text-slate-300">{section.content}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// Main Reports Component
export function Reports() {
  const [selectedReport, setSelectedReport] = useState<ReportType>('daily-summary');
  const [previewReport, setPreviewReport] = useState<ReportData | null>(null);
  const [dateRange, setDateRange] = useState<{ start: Date; end: Date }>({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    end: new Date(),
  });
  const [isGenerating, setIsGenerating] = useState(false);

  const reportTabs = REPORT_TYPES.map(report => ({
    id: report.type,
    label: report.label,
    icon: report.icon,
    content: null,
  }));

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    
    // Simulate generation delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const report = generateReportData(selectedReport, dateRange);
    setPreviewReport(report);
    setIsGenerating(false);
  };

  const handleExport = (format: ExportFormat) => {
    if (!previewReport) return;

    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `${selectedReport}-${timestamp}`;

    switch (format) {
      case 'csv':
        downloadFile(exportToCSV(previewReport), `${filename}.csv`, 'text/csv');
        break;
      case 'excel':
        // For Excel, we use CSV which Excel can open
        downloadFile(exportToCSV(previewReport), `${filename}.csv`, 'text/csv');
        break;
      case 'pdf':
        // Open print dialog for PDF
        window.print();
        break;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Reports</h1>
          <p className="text-sm text-slate-400 mt-1">Generate professional trading reports</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Configuration */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader title="Report Type" />
            <CardContent>
              <Tabs
                tabs={reportTabs}
                variant="pills"
                fullWidth
                onChange={(id) => setSelectedReport(id as ReportType)}
              />
              <p className="text-sm text-slate-400 mt-4">
                {REPORT_TYPES.find(r => r.type === selectedReport)?.description}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Date Range" />
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Start Date</label>
                <input
                  type="date"
                  value={dateRange.start.toISOString().split('T')[0]}
                  onChange={(e) => setDateRange(prev => ({ ...prev, start: new Date(e.target.value) }))}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">End Date</label>
                <input
                  type="date"
                  value={dateRange.end.toISOString().split('T')[0]}
                  onChange={(e) => setDateRange(prev => ({ ...prev, end: new Date(e.target.value) }))}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Export Options" />
            <CardContent className="space-y-2">
              <Button
                variant="primary"
                fullWidth
                onClick={handleGenerateReport}
                loading={isGenerating}
                className="flex items-center justify-center gap-2"
              >
                <DownloadIcon />
                Generate Report
              </Button>
              
              {previewReport && (
                <div className="grid grid-cols-3 gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExport('csv')}
                  >
                    CSV
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExport('excel')}
                  >
                    Excel
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExport('pdf')}
                  >
                    PDF
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Report Preview */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader 
              title="Preview" 
              action={
                <Badge variant="info" size="sm">Preview Only</Badge>
              }
            />
            <CardContent>
              {previewReport ? (
                <ReportPreview report={previewReport} />
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
                    <ChartIcon />
                  </div>
                  <h3 className="text-lg font-medium text-white">No Report Generated</h3>
                  <p className="text-sm text-slate-400 mt-1">
                    Select a report type and click "Generate Report" to preview
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Reports;
