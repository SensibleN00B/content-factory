type StatMetricProps = {
  label: string;
  value: string | number;
  tone?: "default" | "ok" | "error";
};

export function StatMetric({ label, value, tone = "default" }: StatMetricProps) {
  const toneClass = tone === "default" ? "" : ` stat-metric-${tone}`;
  return (
    <div className={`stat-metric${toneClass}`}>
      <p>{label}</p>
      <strong>{value}</strong>
    </div>
  );
}
