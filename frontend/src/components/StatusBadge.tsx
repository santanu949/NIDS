

interface StatusBadgeProps {
  label: string;
  status: 'online' | 'offline' | 'running' | 'stopped' | 'connected' | 'disconnected';
}

export function StatusBadge({ label, status }: StatusBadgeProps) {
  const isGood = status === 'online' || status === 'running' || status === 'connected';
  
  return (
    <div className="flex items-center gap-2.5 px-3.5 py-1.5 bg-slate-50 border border-slate-200 rounded-full shadow-sm">
      <div className={`relative flex h-2.5 w-2.5`}>
        {isGood && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isGood ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
      </div>
      <span className="text-xs font-semibold text-slate-700 tracking-wide uppercase">
        <span className="text-slate-500 mr-1">{label}</span>
        {status}
      </span>
    </div>
  );
}
