type LoadingPanelProps = {
  message: string;
};

export function LoadingPanel({ message }: LoadingPanelProps) {
  return (
    <div className="loading-panel" role="status" aria-live="polite">
      <p>{message}</p>
    </div>
  );
}
