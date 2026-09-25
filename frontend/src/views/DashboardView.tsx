
import { MetricCard } from '../components/MetricCard';
import { Play, Square, Activity, Database, Zap, ShieldAlert, Cpu, Network, ShieldCheck } from 'lucide-react';
import type { PredictionResponse, AnalyticsResponse, LiveStatusResponse } from '../api';

interface DashboardViewProps {
  apiOnline: boolean;
  websocketConnected: boolean;
  liveRunning: boolean;
  liveStatus: LiveStatusResponse | null;
  result: PredictionResponse | null;
  analytics: AnalyticsResponse | null;
  highSeverityCount: number;
  loading: boolean;
  liveLoading: boolean;
  runDemoPrediction: () => void;
  handleLiveToggle: () => void;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function DashboardView({
  apiOnline,
  websocketConnected,
  liveRunning,
  liveStatus,
  result,
  analytics,
  highSeverityCount,
  loading,
  liveLoading,
  runDemoPrediction,
  handleLiveToggle,
}: DashboardViewProps) {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Hero Section */}
      <div className="bg-white border border-slate-200 rounded-2xl p-8 md:p-10 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 p-12 opacity-5 pointer-events-none">
          <ShieldCheck className="w-64 h-64 text-indigo-900" />
        </div>
        
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-600 text-xs font-bold tracking-widest uppercase mb-6">
            Intrusion Detection System
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
            Network activity at a glance
          </h1>
          <p className="text-lg text-slate-500 mb-8 max-w-xl">
            ML-powered binary and multiclass traffic classification securing your network in real-time.
          </p>
          
          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={runDemoPrediction}
              disabled={loading || !apiOnline || liveRunning}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg font-semibold shadow-sm hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <Zap className="w-5 h-5" />
              {loading ? 'Running...' : 'Run Prediction'}
            </button>
            <button
              onClick={handleLiveToggle}
              disabled={liveLoading || !apiOnline || !liveStatus?.interface_configured}
              className={`inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-semibold shadow-sm transition-all border ${
                liveRunning 
                  ? 'bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100 focus:ring-4 focus:ring-rose-50'
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 focus:ring-4 focus:ring-slate-50'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {liveLoading ? (
                <Activity className="w-5 h-5 animate-spin" />
              ) : liveRunning ? (
                <Square className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5" />
              )}
              {liveLoading ? 'Working...' : liveRunning ? 'Stop Live Capture' : 'Start Live Capture'}
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard 
          label="API Status" 
          value={apiOnline ? 'ONLINE' : 'OFFLINE'} 
          description="FastAPI backend" 
          icon={Database} 
          valueColor={apiOnline ? "text-emerald-600" : "text-rose-600"}
        />
        <MetricCard 
          label="Alert Stream" 
          value={websocketConnected ? 'CONNECTED' : 'DISCONNECTED'} 
          description="WebSocket /ws/alerts" 
          icon={Activity} 
          valueColor={websocketConnected ? "text-emerald-600" : "text-rose-600"}
        />
        <MetricCard 
          label="Live Status" 
          value={liveRunning ? 'CAPTURING' : 'STOPPED'} 
          description={liveStatus?.interface_configured ? 'Npcap interface ready' : 'Interface not configured'} 
          icon={Network} 
          valueColor={liveRunning ? "text-indigo-600" : "text-slate-600"}
        />
        <MetricCard 
          label="High Severity" 
          value={highSeverityCount} 
          description="High + critical events" 
          icon={ShieldAlert}
          valueColor={highSeverityCount > 0 ? "text-rose-600" : "text-slate-900"}
        />
        <MetricCard 
          label="Binary Model" 
          value={result?.label ?? '—'} 
          description={result ? `${formatPercent(result.confidence)} confidence` : 'No prediction yet'} 
          icon={Cpu} 
          valueColor={result?.prediction === 1 ? "text-rose-600" : "text-slate-900"}
        />
        <MetricCard 
          label="Attack Category" 
          value={result?.attack_category ?? '—'} 
          description={result ? `${formatPercent(result.multiclass_confidence)} confidence` : 'No prediction yet'} 
          icon={ShieldAlert}
        />
        <MetricCard 
          label="Total Events" 
          value={analytics?.total_events ?? 0} 
          description="Stored predictions" 
          icon={Database} 
        />
        <MetricCard 
          label="Threat Rate" 
          value={analytics ? formatPercent(analytics.attack_rate) : '0.0%'} 
          description="Database-wide rate" 
          icon={Activity} 
        />
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Latest Classification</h2>
            <p className="text-slate-500 text-sm mt-1">Details from the most recent model inference</p>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Binary Result', value: result?.label ?? 'Waiting' },
              { label: 'Attack Category', value: result?.attack_category ?? 'Waiting' },
              { label: 'Binary Confidence', value: result ? formatPercent(result.confidence) : '—' },
              { label: 'Multiclass Confidence', value: result ? formatPercent(result.multiclass_confidence) : '—' },
              { label: 'Severity', value: result?.severity ?? '—' },
              { label: 'Model Version', value: result?.model_version ?? '—' },
            ].map((item, i) => (
              <div key={i} className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                <span className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{item.label}</span>
                <strong className="text-lg text-slate-900">{item.value}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Detection Pipeline</h2>
            <p className="text-slate-500 text-sm mt-1">System processing stages</p>
          </div>
          
          <div className="space-y-3">
            {[
              'Packet capture',
              'Flow aggregation',
              'Feature preprocessing',
              'XGBoost classification',
              'Database persistence',
              'WebSocket alert',
            ].map((step, i) => (
              <div key={i} className="flex items-center p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm flex items-center justify-center mr-4 shrink-0">
                  {String(i + 1).padStart(2, '0')}
                </div>
                <span className="font-medium text-slate-700">{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
