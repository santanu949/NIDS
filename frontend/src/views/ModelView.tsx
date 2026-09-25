import { useMemo } from 'react';
import { MetricCard } from '../components/MetricCard';
import { Database, FileDigit, Cpu, Layers, BarChart, Target, Beaker } from 'lucide-react';
import type { ModelMetricsResponse, ModelFeaturesResponse } from '../api';

interface ModelViewProps {
  modelLoading: boolean;
  modelMetrics: ModelMetricsResponse | null;
  modelFeatures: ModelFeaturesResponse | null;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatMetric(value: number) {
  return value.toFixed(4);
}

function formatFeatureName(name: string) {
  return name.replace(/^num__/, '').replace(/^cat__/, '').replace(/_/g, ' ');
}

export function ModelView({ modelLoading, modelMetrics, modelFeatures }: ModelViewProps) {
  const topFeatures = useMemo(() => {
    if (!modelFeatures) return [];
    return [...modelFeatures.features].sort((a, b) => b.importance - a.importance).slice(0, 15);
  }, [modelFeatures]);

  const maxFeatureImportance = topFeatures.length > 0 
    ? Math.max(...topFeatures.map((f) => f.importance)) 
    : 1;

  if (modelLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] text-slate-500">
        <Cpu className="w-10 h-10 animate-pulse text-indigo-300 mb-4" />
        <p className="font-medium">Loading model evaluation metrics...</p>
      </div>
    );
  }

  if (!modelMetrics || !modelFeatures) return null;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard label="Dataset" value={modelMetrics.dataset} description="Primary training dataset" icon={Database} />
        <MetricCard label="Primary Model" value={modelMetrics.primary_model} description={`Selected by ${modelMetrics.model_selection_metric}`} icon={Cpu} />
        <MetricCard label="Features" value={modelMetrics.transformed_feature_count} description="After preprocessing" icon={Layers} />
        <MetricCard label="Validation Rows" value={modelMetrics.validation_rows.toLocaleString()} description="Held-out validation" icon={FileDigit} />
        <MetricCard label="Multiclass Accuracy" value={formatPercent(modelMetrics.multiclass_accuracy)} description="Validation result" icon={Target} />
        <MetricCard label="Multiclass Macro F1" value={formatPercent(modelMetrics.multiclass_macro_f1)} description="Imbalance-sensitive" icon={BarChart} />
        <MetricCard label="Weighted F1" value={formatPercent(modelMetrics.multiclass_weighted_f1)} description="Multiclass validation" icon={BarChart} />
        <MetricCard label="Official Test" value={modelMetrics.official_test_evaluation_available ? 'EVALUATED' : 'NOT AVAILABLE'} description={modelMetrics.official_test_set_used ? 'Used during development' : 'Held out'} icon={Beaker} valueColor={modelMetrics.official_test_evaluation_available ? "text-emerald-600" : "text-slate-400"} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Binary Evaluation Table */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Binary Evaluation</h2>
            <p className="text-slate-500 text-sm mt-1">Validation metrics used during model selection.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="text-xs text-slate-400 uppercase bg-slate-50">
                <tr>
                  <th className="px-4 py-3 font-semibold rounded-l-lg">Model</th>
                  <th className="px-4 py-3 font-semibold">Accuracy</th>
                  <th className="px-4 py-3 font-semibold">Precision</th>
                  <th className="px-4 py-3 font-semibold">Recall</th>
                  <th className="px-4 py-3 font-semibold">F1</th>
                  <th className="px-4 py-3 font-semibold rounded-r-lg">FPR</th>
                </tr>
              </thead>
              <tbody>
                {modelMetrics.binary_models.map((model) => (
                  <tr key={model.model} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3 font-bold text-slate-900">{model.model}</td>
                    <td className="px-4 py-3">{formatPercent(model.accuracy)}</td>
                    <td className="px-4 py-3">{formatPercent(model.precision)}</td>
                    <td className="px-4 py-3">{formatPercent(model.recall)}</td>
                    <td className="px-4 py-3">{formatPercent(model.f1)}</td>
                    <td className="px-4 py-3">{formatPercent(model.false_positive_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Multiclass Evaluation */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Multiclass Evaluation</h2>
            <p className="text-slate-500 text-sm mt-1">Validation summary for attack categorization.</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Accuracy', value: formatPercent(modelMetrics.multiclass_accuracy) },
              { label: 'Weighted Precision', value: formatPercent(modelMetrics.multiclass_weighted_precision) },
              { label: 'Weighted Recall', value: formatPercent(modelMetrics.multiclass_weighted_recall) },
              { label: 'Weighted F1', value: formatPercent(modelMetrics.multiclass_weighted_f1) },
              { label: 'Macro F1', value: formatPercent(modelMetrics.multiclass_macro_f1) },
              { label: 'Training Rows', value: modelMetrics.training_rows.toLocaleString() },
            ].map((item, idx) => (
              <div key={idx} className="bg-slate-50 border border-slate-100 rounded-xl p-4 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase">{item.label}</span>
                <strong className="text-lg text-slate-900">{item.value}</strong>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Feature Importance */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 lg:p-8">
        <div className="mb-8">
          <h2 className="text-xl font-bold text-slate-900">Feature Importance</h2>
          <p className="text-slate-500 text-sm mt-1">XGBoost feature importance from the trained binary model.</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
          {topFeatures.map((feature) => {
            const width = (feature.importance / maxFeatureImportance) * 100;
            return (
              <div key={feature.name} className="group">
                <div className="flex items-center justify-between text-sm mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded">#{feature.rank}</span>
                    <strong className="text-slate-800 capitalize">{formatFeatureName(feature.name)}</strong>
                  </div>
                  <span className="text-slate-500 font-mono text-xs">{formatMetric(feature.importance)}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-emerald-500 rounded-full transition-all duration-1000 group-hover:bg-emerald-400"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
