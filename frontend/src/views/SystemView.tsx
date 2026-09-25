
import { MetricCard } from '../components/MetricCard';
import { Server, Activity, Network, Timer, AlertTriangle } from 'lucide-react';
import type { LiveStatusResponse } from '../api';

interface SystemViewProps {
  apiOnline: boolean;
  websocketConnected: boolean;
  liveRunning: boolean;
  liveStatus: LiveStatusResponse | null;
}

export function SystemView({ apiOnline, websocketConnected, liveRunning, liveStatus }: SystemViewProps) {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard 
          label="API" 
          value={apiOnline ? 'ONLINE' : 'OFFLINE'} 
          description="FastAPI inference service" 
          icon={Server} 
          valueColor={apiOnline ? "text-emerald-600" : "text-rose-600"}
        />
        <MetricCard 
          label="WebSocket" 
          value={websocketConnected ? 'CONNECTED' : 'DISCONNECTED'} 
          description="Real-time alert channel" 
          icon={Activity} 
          valueColor={websocketConnected ? "text-emerald-600" : "text-rose-600"}
        />
        <MetricCard 
          label="Capture" 
          value={liveRunning ? 'RUNNING' : 'STOPPED'} 
          description="Live packet monitoring" 
          icon={Network} 
          valueColor={liveRunning ? "text-indigo-600" : "text-slate-900"}
        />
        <MetricCard 
          label="Flow Timeout" 
          value={liveStatus ? `${liveStatus.flow_timeout}s` : '—'} 
          description="Live flow aggregation" 
          icon={Timer} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Capture Config */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Capture Configuration</h2>
              <p className="text-slate-500 text-sm mt-1">Network interface details</p>
            </div>
            {liveStatus?.last_error && <AlertTriangle className="w-6 h-6 text-rose-500" />}
          </div>
          
          <div className="space-y-3">
            {[
              { label: 'Interface', value: liveStatus?.interface || 'Not configured' },
              { label: 'Configured', value: liveStatus?.interface_configured ? 'YES' : 'NO' },
              { label: 'Flow Timeout', value: liveStatus ? `${liveStatus.flow_timeout}s` : '—' },
              { label: 'State', value: liveRunning ? 'CAPTURING' : 'STOPPED' },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-sm font-semibold text-slate-600">{item.label}</span>
                <strong className={`text-sm ${item.value === 'YES' || item.value === 'CAPTURING' ? 'text-emerald-600' : 'text-slate-900'}`}>
                  {item.value}
                </strong>
              </div>
            ))}
          </div>

          {liveStatus?.last_error && (
            <div className="mt-4 p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-sm flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <p>{liveStatus.last_error}</p>
            </div>
          )}
        </div>

        {/* Data Flow Architecture */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">System Architecture</h2>
            <p className="text-slate-500 text-sm mt-1">Application data flow</p>
          </div>
          
          <div className="relative">
            {/* Connecting line */}
            <div className="absolute left-[1.15rem] top-4 bottom-4 w-0.5 bg-slate-100" />
            
            <div className="space-y-4 relative z-10">
              {[
                { step: '01', title: 'UNSW-NB15 / Live Traffic', desc: 'Raw packet ingestion' },
                { step: '02', title: 'Feature Extraction', desc: 'Flow feature generation' },
                { step: '03', title: 'Preprocessor Artifact', desc: 'Standard scaling & encoding' },
                { step: '04', title: 'Binary XGBoost', desc: 'Normal vs Attack classification' },
                { step: '05', title: 'Multiclass XGBoost', desc: 'Attack categorization' },
                { step: '06', title: 'SQLAlchemy Persistence', desc: 'Database logging' },
                { step: '07', title: 'React + WebSocket', desc: 'Real-time UI updates' },
              ].map((item, i) => (
                <div key={i} className="flex gap-4 group">
                  <div className="w-10 h-10 rounded-full bg-white border-2 border-indigo-100 text-indigo-600 font-bold text-sm flex items-center justify-center shrink-0 group-hover:border-indigo-500 group-hover:bg-indigo-50 transition-colors">
                    {item.step}
                  </div>
                  <div className="pt-2">
                    <strong className="block text-sm text-slate-900">{item.title}</strong>
                    <span className="text-xs text-slate-500">{item.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
}
