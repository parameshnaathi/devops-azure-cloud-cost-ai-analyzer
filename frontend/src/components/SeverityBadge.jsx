const SEVERITY_STYLES = {
  high: { background: "#fde2e1", color: "#9b1c1c", border: "#f5b5b3" },
  medium: { background: "#fef3c7", color: "#92660a", border: "#fadb8f" },
  low: { background: "#dcfce7", color: "#166534", border: "#a7e3bd" },
};

export default function SeverityBadge({ severity }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.low;
  return (
    <span
      className="severity-badge"
      style={{
        backgroundColor: style.background,
        color: style.color,
        borderColor: style.border,
      }}
    >
      {severity?.toUpperCase() || "LOW"}
    </span>
  );
}
