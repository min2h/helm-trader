export function LoadingBar({ show, label }: { show: boolean; label?: string }) {
  if (!show) return null;
  return (
    <div className="loading-wrap" role="status" aria-live="polite">
      <div className="loading-bar" />
      {label ? <p className="muted loading-label">{label}</p> : null}
    </div>
  );
}
