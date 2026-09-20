// Both /api/analyze and /api/history return analysis data, but with slightly
// different shapes. This normalizes both into one consistent object for the
// Report page.
export function normalizeAnalysis(source) {
  if (!source) {
    return null;
  }

  // History row: { id, resource_group, resources_scanned, issues_found,
  //                estimated_savings, analysis_result: {...}, status, created_at }
  if (source.analysis_result) {
    const result = source.analysis_result;
    const aiAnalysis = result.ai_analysis || {};
    return {
      id: source.id,
      resourceGroup: result.resource_group ?? source.resource_group,
      resourceCount: result.resource_count ?? source.resources_scanned ?? 0,
      resources: result.resources ?? [],
      summaryText: aiAnalysis.summary ?? "",
      issues: aiAnalysis.issues ?? [],
      issuesFound: source.issues_found ?? (aiAnalysis.issues ?? []).length,
      estimatedSavingsText: source.estimated_savings ?? formatSavings(aiAnalysis.estimated_savings),
      fixCommands: aiAnalysis.fix_commands ?? [],
      status: source.status ?? "completed",
      createdAt: source.created_at ?? null,
    };
  }

  // Live /api/analyze response: { analysis_id, resource_group, resource_count,
  //                                resources, summary, ai_analysis }
  const aiAnalysis = source.ai_analysis || {};
  return {
    id: source.analysis_id,
    resourceGroup: source.resource_group,
    resourceCount: source.resource_count ?? 0,
    resources: source.resources ?? [],
    summaryText: aiAnalysis.summary ?? "",
    issues: aiAnalysis.issues ?? [],
    issuesFound: (aiAnalysis.issues ?? []).length,
    estimatedSavingsText: formatSavings(aiAnalysis.estimated_savings),
    fixCommands: aiAnalysis.fix_commands ?? [],
    status: "completed",
    createdAt: new Date().toISOString(),
  };
}

function formatSavings(savings) {
  if (!savings) return "$0.00 USD/mo";
  const amount = Number(savings.monthly_usd ?? 0).toFixed(2);
  return `$${amount} ${savings.currency ?? "USD"}/mo`;
}
