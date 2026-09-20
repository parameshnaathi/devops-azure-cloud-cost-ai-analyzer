export default function SummaryCard({ resourceCount, issuesFound, estimatedSavingsText, summary }) {
  return (
    <div className="summary-card">
      <div className="summary-stats">
        <div className="stat">
          <span className="stat-value">{resourceCount ?? 0}</span>
          <span className="stat-label">Resources Scanned</span>
        </div>
        <div className="stat">
          <span className="stat-value">{issuesFound ?? 0}</span>
          <span className="stat-label">Issues Found</span>
        </div>
        <div className="stat stat-savings">
          <span className="stat-value">{estimatedSavingsText || "$0.00 USD/mo"}</span>
          <span className="stat-label">Estimated Savings</span>
        </div>
      </div>
      {summary && <p className="summary-text">{summary}</p>}
    </div>
  );
}
