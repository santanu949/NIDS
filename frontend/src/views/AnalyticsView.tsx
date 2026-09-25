import { useMemo } from 'react';
import { MetricCard } from '../components/MetricCard';
import { Database, ShieldAlert, Activity, CheckCircle, Percent, Target } from 'lucide-react';
import type { AnalyticsResponse } from '../api';

interface AnalyticsViewProps {
  analytics: AnalyticsResponse | null;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function AnalyticsView({ analytics }: AnalyticsViewProps) {
  const sortedAttackCategories = useMemo(() => {
    if (!analytics) return [];
    return Object.entries(analytics.attack_categories)
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  }, [analytics]);

  const maxAttackCategoryCount = sortedAttackCategories.length > 0 
    ? Math.max(...sortedAttackCategories.map((item) => item.count)) 
    : 1;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <MetricCard 
          label="Total Events" 
          value={analytics?.total_events ?? 0} 
          description="Persisted predictions" 
          icon={Database} 
        />
        <MetricCard 
          label="Normal" 
          value={analytics?.normal_events ?? 0} 
          description="Binary normal classifications" 
          icon={CheckCircle} 
          valueColor="text-emerald-600"
        />
        <MetricCard 
          label="Attacks" 
          value={analytics?.attack_events ?? 0} 
          description="Binary attack classifications" 
          icon={ShieldAlert}
          valueColor={analytics?.attack_events ? "text-rose-600" : "text-slate-900"}
        />
        <MetricCard 
          label="Threat Rate" 
          value={analytics ? formatPercent(analytics.attack_rate) : '0.0%'} 
          description="Attack / Total" 
          icon={Activity} 
        />
        <MetricCard 
          label="Binary Confidence" 
          value={analytics ? formatPercent(analytics.average_binary_confidence) : '0.0%'} 
          description="Average stored confidence" 
          icon={Target} 
        />
        <MetricCard 
          label="Multiclass Confidence" 
          value={analytics ? formatPercent(analytics.average_multiclass_confidence) : '0.0%'} 
          description="Average category confidence" 
          icon={Percent} 
        />
      </div>

      {/* Attack Distribution */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
        <div className="mb-8">
          <h2 className="text-xl font-bold text-slate-900">Attack Distribution</h2>
          <p className="text-slate-500 text-sm mt-1">Stored attack categories based on prediction database.</p>
        </div>

        {sortedAttackCategories.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <ShieldAlert className="w-10 h-10 text-slate-300 mb-3" />
            <p className="text-slate-500 font-medium">No attack category data available.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedAttackCategories.map((item) => {
              const width = (item.count / maxAttackCategoryCount) * 100;
              return (
                <div key={item.category} className="group relative">
                  <div className="flex justify-between text-sm font-semibold mb-1.5">
                    <span className="text-slate-700">{item.category}</span>
                    <span className="text-slate-900">{item.count.toLocaleString()}</span>
                  </div>
                  <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-500 rounded-full transition-all duration-1000 group-hover:bg-indigo-600"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
