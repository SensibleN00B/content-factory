type StatusBadgeProps = {
  value: string;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value.trim().toLowerCase();
  return <span className={`status-badge status-${normalized}`}>{value}</span>;
}
