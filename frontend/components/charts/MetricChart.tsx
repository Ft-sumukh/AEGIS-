"use client";

import React, { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Anomaly } from "@/lib/api/types";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

export interface ChartDataPoint {
  timestamp: string;
  timeLabel: string;
  value: number;
  baseline?: number;
  isAnomaly?: boolean;
  anomalyDetails?: Anomaly;
  isDeployment?: boolean;
  deploymentVersion?: string;
}

interface MetricChartProps {
  title: string;
  unit: string;
  data: ChartDataPoint[];
  incidentWindow?: {
    start: string;
    end: string;
    label?: string;
  };
  deploymentTimestamp?: string;
  deploymentLabel?: string;
  color?: string;
  height?: number;
}

export function MetricChart({
  title,
  unit,
  data,
  incidentWindow,
  deploymentTimestamp,
  deploymentLabel = "v4.8.2 Deployed",
  color = "#06b6d4", // cyan
  height = 280,
}: MetricChartProps) {
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null);

  if (!data || data.length === 0) {
    return (
      <div
        style={{ height }}
        className="rounded-xl border border-slate-800 bg-slate-950/40 flex items-center justify-center text-slate-500 text-xs font-mono"
      >
        No telemetry data available for {title}
      </div>
    );
  }

  // Filter anomalies for scatter layer
  const anomalyPoints = data
    .filter((d) => d.isAnomaly && d.anomalyDetails)
    .map((d) => ({
      timeLabel: d.timeLabel,
      value: d.value,
      anomaly: d.anomalyDetails,
    }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold font-mono text-slate-200 tracking-wide uppercase">
            {title}
          </h4>
          <p className="text-xs text-slate-400">
            Telemetry time-series with baseline, anomaly correlation, and deployment tracking ({unit})
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-0.5 bg-cyan-400 inline-block" />
            <span>Observed</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2.5 h-0.5 border-t border-dashed border-slate-500 inline-block" />
            <span>Baseline</span>
          </div>
          {anomalyPoints.length > 0 && (
            <div className="flex items-center gap-1.5 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
              <span>Anomaly</span>
            </div>
          )}
        </div>
      </div>

      <div style={{ height, width: "100%" }} className="relative">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${title}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

            <XAxis
              dataKey="timeLabel"
              stroke="#64748b"
              fontSize={11}
              fontFamily="monospace"
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              fontFamily="monospace"
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              tickFormatter={(v) => `${v}`}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const pt = payload[0].payload as ChartDataPoint;
                  return (
                    <div className="rounded-lg border border-slate-700 bg-slate-900/95 p-3 shadow-xl backdrop-blur text-xs font-mono space-y-1.5">
                      <div className="text-slate-400">{pt.timestamp}</div>
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-slate-300">Observed:</span>
                        <span className="font-bold text-white">
                          {pt.value} {unit}
                        </span>
                      </div>
                      {pt.baseline !== undefined && (
                        <div className="flex items-center justify-between gap-4 text-slate-400">
                          <span>Baseline:</span>
                          <span>
                            {pt.baseline} {unit}
                          </span>
                        </div>
                      )}
                      {pt.isAnomaly && (
                        <div className="text-rose-400 font-semibold pt-1 border-t border-slate-800">
                          ● Anomaly Detected
                        </div>
                      )}
                      {pt.isDeployment && (
                        <div className="text-amber-400 font-semibold pt-1 border-t border-slate-800">
                          ◆ {pt.deploymentVersion || "Deployment Event"}
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />

            {/* Shaded Incident Window */}
            {incidentWindow && (
              <ReferenceArea
                x1={incidentWindow.start}
                x2={incidentWindow.end}
                stroke="#f43f5e"
                strokeOpacity={0.2}
                fill="#f43f5e"
                fillOpacity={0.06}
              />
            )}

            {/* Vertical Deployment Marker */}
            {deploymentTimestamp && (
              <ReferenceLine
                x={deploymentTimestamp}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                strokeWidth={2}
                label={{
                  value: deploymentLabel,
                  position: "top",
                  fill: "#f59e0b",
                  fontSize: 10,
                  fontFamily: "monospace",
                }}
              />
            )}

            {/* Baseline Line if present */}
            <Area
              type="monotone"
              dataKey="baseline"
              stroke="#64748b"
              strokeDasharray="3 3"
              fill="transparent"
              strokeWidth={1}
              isAnimationActive={false}
            />

            {/* Main Metric Area */}
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#grad-${title})`}
              isAnimationActive={false}
            />

            {/* Anomalies Scatter Overlay */}
            {anomalyPoints.length > 0 && (
              <Scatter
                data={anomalyPoints}
                fill="#f43f5e"
                shape="circle"
                onClick={(node) => {
                  if (node && (node as any).anomaly) {
                    setSelectedAnomaly((node as any).anomaly);
                  }
                }}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Interactive Anomaly Detail Inspector (Click to inspect) */}
      {selectedAnomaly && (
        <div className="p-3 rounded-lg border border-rose-900/60 bg-rose-950/20 text-xs font-mono flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 animate-fadeIn">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-rose-400 font-bold uppercase">Detected Anomaly</span>
              <SeverityBadge severity={selectedAnomaly.severity} size="sm" />
              <span className="text-slate-400 text-[11px]">{selectedAnomaly.detected_at}</span>
            </div>
            <p className="text-slate-300 font-sans text-xs">{selectedAnomaly.explanation}</p>
            <div className="text-[11px] text-slate-400 flex gap-4 pt-1">
              <span>Observed: {selectedAnomaly.observed_value}</span>
              <span>Expected: {selectedAnomaly.expected_value}</span>
              <span>Deviation: +{selectedAnomaly.deviation}</span>
              <span>Detector: {selectedAnomaly.detector_type}</span>
              <span>Confidence: {Math.round(selectedAnomaly.confidence * 100)}%</span>
            </div>
          </div>
          <button
            onClick={() => setSelectedAnomaly(null)}
            className="text-slate-400 hover:text-slate-200 text-xs font-mono px-2 py-1 bg-slate-900 rounded border border-slate-800"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
