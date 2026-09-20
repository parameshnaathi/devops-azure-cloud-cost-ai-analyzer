import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../api";

export default function HistoryPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getHistory(token)
      .then((data) => {
        if (!cancelled) setHistory(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load history.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const openReport = (entry) => {
    navigate("/report", { state: { analysis: entry } });
  };

  return (
    <div className="page">
      <h1>Analysis History</h1>

      {loading && <p>Loading history...</p>}
      {error && <p className="form-error">{error}</p>}

      {!loading && !error && history.length === 0 && (
        <p>No past analyses yet. Run one from the Dashboard.</p>
      )}

      {!loading && history.length > 0 && (
        <table className="history-table">
          <thead>
            <tr>
              <th>Resource Group</th>
              <th>Date</th>
              <th>Resources</th>
              <th>Issues</th>
              <th>Est. Savings</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {history.map((entry) => (
              <tr key={entry.id} onClick={() => openReport(entry)} className="history-row">
                <td>{entry.resource_group}</td>
                <td>{new Date(entry.created_at).toLocaleString()}</td>
                <td>{entry.resources_scanned}</td>
                <td>{entry.issues_found}</td>
                <td>{entry.estimated_savings}</td>
                <td>
                  <span className={`status-pill status-${entry.status}`}>{entry.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
