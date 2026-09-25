import { useState, useMemo } from 'react';
import { Search, Download, Filter, X } from 'lucide-react';
import type { PredictionEvent } from '../api';

interface DetectionsViewProps {
  events: PredictionEvent[];
  websocketConnected: boolean;
}

const severityOrder: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function DetectionsView({ events, websocketConnected }: DetectionsViewProps) {
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [modeFilter, setModeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<PredictionEvent | null>(null);

  const categories = useMemo(() => {
    return Array.from(new Set(events.map((event) => event.attack_category))).sort();
  }, [events]);

  const filteredEvents = useMemo(() => {
    const search = searchFilter.trim().toLowerCase();

    return events
      .filter((event) => {
        if (categoryFilter !== 'all' && event.attack_category !== categoryFilter) return false;
        if (severityFilter !== 'all' && event.severity !== severityFilter) return false;
        if (modeFilter !== 'all' && event.mode !== modeFilter) return false;
        if (statusFilter === 'attack' && event.binary_prediction !== 1) return false;
        if (statusFilter === 'normal' && event.binary_prediction !== 0) return false;

        if (!search) return true;

        const searchable = [
          String(event.id),
          event.mode,
          event.source_ip ?? '',
          event.destination_ip ?? '',
          event.protocol ?? '',
          event.binary_label,
          event.attack_category,
          event.severity,
          event.model_version,
        ].join(' ').toLowerCase();

        return searchable.includes(search);
      })
      .sort((a, b) => {
        const severityDifference = (severityOrder[b.severity] ?? 0) - (severityOrder[a.severity] ?? 0);
        if (severityDifference !== 0) return severityDifference;
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      });
  }, [events, categoryFilter, severityFilter, modeFilter, statusFilter, searchFilter]);

  const resetFilters = () => {
    setCategoryFilter('all');
    setSeverityFilter('all');
    setModeFilter('all');
    setStatusFilter('all');
    setSearchFilter('');
  };

  const exportEvents = () => {
    const headers = ['id', 'timestamp', 'mode', 'source_ip', 'destination_ip', 'protocol', 'binary_prediction', 'binary_label', 'binary_confidence', 'attack_category', 'multiclass_confidence', 'severity', 'model_version'];
    const escapeCsv = (value: unknown) => {
      const stringValue = value == null ? '' : String(value);
      return `"${stringValue.replaceAll('"', '""')}"`;
    };

    const rows = filteredEvents.map((event) =>
      [event.id, event.timestamp, event.mode, event.source_ip, event.destination_ip, event.protocol, event.binary_prediction, event.binary_label, event.binary_confidence, event.attack_category, event.multiclass_confidence, event.severity, event.model_version]
        .map(escapeCsv)
        .join(',')
    );

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'nids-detections.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 flex flex-col h-[calc(100vh-8rem)]">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col h-full shrink-0">
        
        {/* Header & Filters */}
        <div className="p-6 border-b border-slate-200 bg-slate-50/50">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Detection History</h2>
              <p className="text-slate-500 text-sm mt-1">Search and filter stored prediction events.</p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={resetFilters} className="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 focus:ring-2 focus:ring-slate-200 transition-colors">
                Reset
              </button>
              <button onClick={exportEvents} className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 border border-indigo-100 rounded-lg hover:bg-indigo-100 focus:ring-2 focus:ring-indigo-200 transition-colors">
                <Download className="w-4 h-4" /> Export CSV
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input type="search" value={searchFilter} onChange={(e) => setSearchFilter(e.target.value)} placeholder="Search ID, IP, protocol..." className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" />
            </div>
            
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 appearance-none">
              <option value="all">All Statuses</option>
              <option value="attack">Attack Only</option>
              <option value="normal">Normal Only</option>
            </select>

            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="w-full px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 appearance-none">
              <option value="all">All Categories</option>
              {categories.map((c) => (<option key={c} value={c}>{c}</option>))}
            </select>

            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="w-full px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 appearance-none">
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select value={modeFilter} onChange={(e) => setModeFilter(e.target.value)} className="w-full px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 appearance-none">
              <option value="all">All Modes</option>
              <option value="dataset">Dataset</option>
              <option value="live">Live</option>
            </select>
          </div>
          
          <div className="flex items-center justify-between mt-4 text-xs font-medium text-slate-500">
            <span>Showing <strong className="text-slate-900">{filteredEvents.length}</strong> of {events.length} events</span>
            <span>WebSocket: {websocketConnected ? <strong className="text-emerald-600">Connected</strong> : <span className="text-amber-600">Fallback Polling</span>}</span>
          </div>
        </div>

        {/* List Content */}
        <div className="flex-1 overflow-auto p-6 bg-slate-50/30">
          {filteredEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                <Filter className="w-8 h-8 text-slate-400" />
              </div>
              <h3 className="text-lg font-medium text-slate-900">No events found</h3>
              <p className="text-slate-500 mt-1">Adjust your filters or search query to find events.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredEvents.slice(0, 50).map((event) => (
                <button 
                  key={event.id} 
                  onClick={() => setSelectedEvent(event)}
                  className="w-full flex items-center justify-between text-left p-4 bg-white border border-slate-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all group focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <div className="flex items-center gap-6">
                    <div className="w-16">
                      <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-1 rounded-md">#{event.id}</span>
                    </div>
                    
                    <div className="w-32">
                      <strong className={`block text-sm font-bold ${event.binary_prediction ? 'text-rose-600' : 'text-emerald-600'}`}>
                        {event.binary_label}
                      </strong>
                      <span className="text-xs text-slate-500">{event.mode.toUpperCase()}</span>
                    </div>

                    <div className="w-48 hidden sm:block">
                      <strong className="block text-sm font-semibold text-slate-900 truncate">
                        {event.attack_category}
                      </strong>
                      <span className="text-xs text-slate-500">Cat: {formatPercent(event.multiclass_confidence)}</span>
                    </div>

                    <div className="w-24 hidden md:block">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider
                        ${event.severity === 'critical' ? 'bg-rose-100 text-rose-700' :
                          event.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                          event.severity === 'medium' ? 'bg-amber-100 text-amber-700' :
                          'bg-slate-100 text-slate-700'}
                      `}>
                        {event.severity}
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="block text-xs font-medium text-slate-900 tabular-nums">
                      {new Date(event.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })}
                    </span>
                    <span className="text-[11px] text-slate-400 tabular-nums">
                      {new Date(event.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail Panel */}
      {selectedEvent && (
        <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white border-l border-slate-200 shadow-2xl p-6 overflow-y-auto z-50 animate-in slide-in-from-right duration-300">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h3 className="text-xl font-bold text-slate-900">Event #{selectedEvent.id}</h3>
              <p className="text-sm text-slate-500">Full classification record</p>
            </div>
            <button onClick={() => setSelectedEvent(null)} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
              <X className="w-6 h-6" />
            </button>
          </div>
          
          <div className="space-y-4">
            {[
              { label: 'Timestamp', value: new Date(selectedEvent.timestamp).toLocaleString() },
              { label: 'Mode', value: selectedEvent.mode },
              { label: 'Source IP', value: selectedEvent.source_ip ?? 'N/A' },
              { label: 'Destination IP', value: selectedEvent.destination_ip ?? 'N/A' },
              { label: 'Protocol', value: selectedEvent.protocol ?? 'N/A' },
              { label: 'Binary Prediction', value: selectedEvent.binary_label },
              { label: 'Binary Confidence', value: formatPercent(selectedEvent.binary_confidence) },
              { label: 'Attack Category', value: selectedEvent.attack_category },
              { label: 'Multiclass Confidence', value: formatPercent(selectedEvent.multiclass_confidence) },
              { label: 'Severity', value: selectedEvent.severity },
              { label: 'Model Version', value: selectedEvent.model_version },
            ].map((detail, idx) => (
              <div key={idx} className="bg-slate-50 border border-slate-100 rounded-lg p-3">
                <span className="block text-xs font-semibold text-slate-500 uppercase mb-1">{detail.label}</span>
                <strong className="text-sm text-slate-900">{detail.value}</strong>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
