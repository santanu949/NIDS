
import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  description?: string;
  icon?: LucideIcon;
  valueColor?: string;
}

export function MetricCard({ label, value, description, icon: Icon, valueColor = "text-slate-900" }: MetricCardProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">{label}</h3>
        {Icon && <Icon className="w-5 h-5 text-indigo-500 opacity-80" strokeWidth={2} />}
      </div>
      <div className="mt-auto">
        <span className={`text-3xl font-extrabold tracking-tight ${valueColor}`}>{value}</span>
        {description && (
          <p className="mt-1.5 text-sm font-medium text-slate-500">{description}</p>
        )}
      </div>
    </div>
  );
}
