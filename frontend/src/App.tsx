import { useEffect, useState } from 'react';
import { 
  checkHealth, 
  connectToAlerts, 
  getAnalytics, 
  getEvents, 
  getLiveStatus, 
  getModelFeatures, 
  getModelMetrics, 
  predict, 
  startLiveCapture, 
  stopLiveCapture 
} from './api';
import type { 
  AnalyticsResponse, 
  LiveStatusResponse, 
  ModelFeaturesResponse, 
  ModelMetricsResponse, 
  PredictionEvent, 
  PredictionResponse, 
  WebSocketAlert 
} from './api';

import { StatusBadge } from './components/StatusBadge';
import { DashboardView } from './views/DashboardView';
import { DetectionsView } from './views/DetectionsView';
import { AnalyticsView } from './views/AnalyticsView';
import { ModelView } from './views/ModelView';
import { SystemView } from './views/SystemView';

import { ShieldCheck, LayoutDashboard, List, BarChart3, BrainCircuit, Server, AlertTriangle } from 'lucide-react';

const demoFeatures: Record<string, unknown> = {
  dur: 0.121478, proto: 'tcp', service: '-', state: 'FIN', spkts: 6, dpkts: 4, sbytes: 258, dbytes: 172, rate: 74.08749, sttl: 252, dttl: 254, sload: 14158.94238, dload: 8495.365234, sloss: 0, dloss: 0, sinpkt: 24.2956, dinpkt: 8.375, sjit: 30.177547, djit: 11.830604, swin: 255, stcpb: 621772692, dtcpb: 2202533631, dwin: 255, tcprtt: 0, synack: 0, ackdat: 0, smean: 43, dmean: 43, trans_depth: 0, response_body_len: 0, ct_srv_src: 1, ct_state_ttl: 0, ct_dst_ltm: 1, ct_src_dport_ltm: 1, ct_dst_sport_ltm: 1, ct_dst_src_ltm: 1, is_ftp_login: 0, ct_ftp_cmd: 0, ct_flw_http_mthd: 0, ct_src_ltm: 1, ct_srv_dst: 1, is_sm_ips_ports: 0,
};

type ViewName = 'dashboard' | 'detections' | 'analytics' | 'model' | 'system';

function App() {
  const [activeView, setActiveView] = useState<ViewName>('dashboard');
  const [apiOnline, setApiOnline] = useState(false);
  const [websocketConnected, setWebsocketConnected] = useState(false);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [events, setEvents] = useState<PredictionEvent[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelMetricsResponse | null>(null);
  const [modelFeatures, setModelFeatures] = useState<ModelFeaturesResponse | null>(null);
  const [liveStatus, setLiveStatus] = useState<LiveStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [liveLoading, setLiveLoading] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [error, setError] = useState('');

  const loadDashboardData = async () => {
    try {
      const [eventData, analyticsData] = await Promise.all([getEvents(), getAnalytics()]);
      setEvents(eventData);
      setAnalytics(analyticsData);
      if (eventData.length > 0) {
        const latest = eventData[0];
        setResult({
          prediction: latest.binary_prediction,
          label: latest.binary_label,
          confidence: latest.binary_confidence,
          attack_category: latest.attack_category,
          multiclass_confidence: latest.multiclass_confidence,
          severity: latest.severity,
          model_version: latest.model_version,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    }
  };

  const loadLiveStatus = async () => {
    try {
      const status = await getLiveStatus();
      setLiveStatus(status);
    } catch {
      setLiveStatus(null);
    }
  };

  const loadModelData = async () => {
    setModelLoading(true);
    try {
      const [metrics, features] = await Promise.all([getModelMetrics(), getModelFeatures()]);
      setModelMetrics(metrics);
      setModelFeatures(features);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model data');
    } finally {
      setModelLoading(false);
    }
  };

  useEffect(() => {
    let websocket: WebSocket | null = null;
    checkHealth()
      .then(() => {
        setApiOnline(true);
        void loadDashboardData();
        void loadLiveStatus();
        void loadModelData();
        websocket = connectToAlerts(
          (alert: WebSocketAlert) => {
            if (alert.event !== 'prediction') return;
            const detection = alert.detection;
            
            setEvents((currentEvents) => {
              const withoutDuplicate = currentEvents.filter((event) => event.id !== detection.id);
              return [detection, ...withoutDuplicate].slice(0, 100);
            });
            
            setResult({
              prediction: detection.binary_prediction,
              label: detection.binary_label,
              confidence: detection.binary_confidence,
              attack_category: detection.attack_category,
              multiclass_confidence: detection.multiclass_confidence,
              severity: detection.severity,
              model_version: detection.model_version,
            });
            
            setAnalytics((currentAnalytics) => {
              if (!currentAnalytics) return currentAnalytics;
              const isAttack = detection.binary_prediction === 1;
              const category = detection.attack_category;
              const nextTotal = currentAnalytics.total_events + 1;
              const nextAttackCount = currentAnalytics.attack_events + (isAttack ? 1 : 0);
              return {
                ...currentAnalytics,
                total_events: nextTotal,
                normal_events: currentAnalytics.normal_events + (isAttack ? 0 : 1),
                attack_events: nextAttackCount,
                attack_rate: nextTotal > 0 ? nextAttackCount / nextTotal : 0,
                attack_categories: {
                  ...currentAnalytics.attack_categories,
                  [category]: (currentAnalytics.attack_categories[category] ?? 0) + 1,
                },
              };
            });
          },
          (connected: boolean) => setWebsocketConnected(connected)
        );
      })
      .catch(() => {
        setApiOnline(false);
        setWebsocketConnected(false);
      });
    return () => { websocket?.close(); };
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (apiOnline) {
        void loadLiveStatus();
        void loadDashboardData();
      }
    }, 2000);
    return () => window.clearInterval(interval);
  }, [apiOnline]);

  const runDemoPrediction = async () => {
    setLoading(true);
    setError('');
    try {
      const prediction = await predict(demoFeatures, 'dataset');
      setResult(prediction);
      setApiOnline(true);
      await loadDashboardData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed');
      setApiOnline(false);
    } finally {
      setLoading(false);
    }
  };

  const handleLiveToggle = async () => {
    setLiveLoading(true);
    setError('');
    try {
      const status = liveStatus?.running ? await stopLiveCapture() : await startLiveCapture();
      setLiveStatus(status);
      setApiOnline(true);
      await loadDashboardData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Live capture operation failed');
      await loadLiveStatus();
    } finally {
      setLiveLoading(false);
    }
  };

  const highSeverityCount = events.filter((e) => e.severity === 'high' || e.severity === 'critical').length;
  const liveRunning = liveStatus?.running ?? false;

  const navItems = [
    { id: 'dashboard' as const, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'detections' as const, label: 'Detections', icon: List },
    { id: 'analytics' as const, label: 'Analytics', icon: BarChart3 },
    { id: 'model' as const, label: 'Model', icon: BrainCircuit },
    { id: 'system' as const, label: 'System', icon: Server },
  ];

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans overflow-hidden">
      
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex-col hidden md:flex shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <ShieldCheck className="w-6 h-6 text-indigo-600 mr-2.5" />
          <span className="text-lg font-bold tracking-tight text-slate-900">NIDS-ML</span>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${
                activeView === item.id 
                  ? 'bg-indigo-50 text-indigo-700' 
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <item.icon className={`w-5 h-5 ${activeView === item.id ? 'text-indigo-600' : 'text-slate-400'}`} />
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 lg:px-8 shrink-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold capitalize text-slate-800 hidden sm:block">
              {activeView}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge label="API" status={apiOnline ? 'online' : 'offline'} />
            <StatusBadge label="WS" status={websocketConnected ? 'connected' : 'disconnected'} />
          </div>
        </header>

        {/* Scrollable Main Content */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          {/* Global Error Banner */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0" />
              <p className="text-sm font-medium text-rose-700">{error}</p>
            </div>
          )}

          {activeView === 'dashboard' && (
            <DashboardView 
              apiOnline={apiOnline}
              websocketConnected={websocketConnected}
              liveRunning={liveRunning}
              liveStatus={liveStatus}
              result={result}
              analytics={analytics}
              highSeverityCount={highSeverityCount}
              loading={loading}
              liveLoading={liveLoading}
              runDemoPrediction={runDemoPrediction}
              handleLiveToggle={handleLiveToggle}
            />
          )}

          {activeView === 'detections' && (
            <DetectionsView 
              events={events}
              websocketConnected={websocketConnected}
            />
          )}

          {activeView === 'analytics' && (
            <AnalyticsView analytics={analytics} />
          )}

          {activeView === 'model' && (
            <ModelView 
              modelLoading={modelLoading}
              modelMetrics={modelMetrics}
              modelFeatures={modelFeatures}
            />
          )}

          {activeView === 'system' && (
            <SystemView 
              apiOnline={apiOnline}
              websocketConnected={websocketConnected}
              liveRunning={liveRunning}
              liveStatus={liveStatus}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;