import SeverityBadge from "./SeverityBadge";
import CopyableCode from "./CopyableCode";

const ISSUE_TYPE_LABELS = {
  over_provisioned: "Over-Provisioned",
  unused: "Unused",
  misconfigured: "Misconfigured",
  wrong_pricing_tier: "Wrong Pricing Tier",
  other: "Other",
};

function formatIssueType(issueType) {
  return (
    ISSUE_TYPE_LABELS[issueType] ||
    (issueType || "other")
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  );
}

export default function IssueCard({ issue }) {
  return (
    <div className="issue-card">
      <div className="issue-card-header">
        <div>
          <h3>{issue.resource_name}</h3>
          <span className="issue-type-pill">{formatIssueType(issue.issue_type)}</span>
        </div>
        <SeverityBadge severity={issue.severity} />
      </div>
      <p className="issue-description">{issue.description}</p>
      {issue.recommendation && (
        <p className="issue-recommendation">
          <strong>Recommendation:</strong> {issue.recommendation}
        </p>
      )}
      <CopyableCode command={issue.fix_command} />
    </div>
  );
}
