import { Link, useLocation, useNavigate } from "react-router-dom";
import SummaryCard from "../components/SummaryCard";
import IssueCard from "../components/IssueCard";
import ResourceTable from "../components/ResourceTable";
import { normalizeAnalysis } from "../utils/normalizeAnalysis";

export default function ReportPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const analysis = normalizeAnalysis(location.state?.analysis);

  if (!analysis) {
    return (
      <div className="page">
        <h1>No analysis to display</h1>
        <p>
          Run a new analysis from the <Link to="/">Dashboard</Link> or pick one from{" "}
          <Link to="/history">History</Link>.
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <button type="button" className="link-button back-button" onClick={() => navigate(-1)}>
        &larr; Back
      </button>
      <h1>Analysis Report: {analysis.resourceGroup}</h1>
      {analysis.createdAt && (
        <p className="report-timestamp">
          {new Date(analysis.createdAt).toLocaleString()} &middot; status: {analysis.status}
        </p>
      )}

      <SummaryCard
        resourceCount={analysis.resourceCount}
        issuesFound={analysis.issuesFound}
        estimatedSavingsText={analysis.estimatedSavingsText}
        summary={analysis.summaryText}
      />

      <h2>Issues</h2>
      {analysis.issues.length === 0 ? (
        <p>No issues found. This resource group looks well optimized!</p>
      ) : (
        <div className="issue-list">
          {analysis.issues.map((issue, index) => (
            <IssueCard key={`${issue.resource_name}-${index}`} issue={issue} />
          ))}
        </div>
      )}

      <h2>Scanned Resources</h2>
      <ResourceTable resources={analysis.resources} />
    </div>
  );
}
