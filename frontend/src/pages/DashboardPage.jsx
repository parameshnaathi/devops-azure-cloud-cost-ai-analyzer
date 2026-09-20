import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, ApiError, WS_BASE_URL } from "../api";
import ProgressTracker from "../components/ProgressTracker";

export default function DashboardPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [resourceGroups, setResourceGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState("");
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [isRunning, setIsRunning] = useState(false);
  const [progressMessages, setProgressMessages] = useState([]);
  const [runError, setRunError] = useState("");

  const socketRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingGroups(true);
    api
      .getResourceGroups(token)
      .then((groups) => {
        if (cancelled) return;
        setResourceGroups(groups);
        if (groups.length > 0) {
          setSelectedGroup(groups[0].name);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof ApiError ? err.message : "Failed to load resource groups.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingGroups(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  const runAnalysis = async () => {
    if (!selectedGroup || isRunning) return;

    setIsRunning(true);
    setRunError("");
    setProgressMessages([]);

    const analysisId = crypto.randomUUID();
    const socket = new WebSocket(
      `${WS_BASE_URL}/ws/progress/${analysisId}?token=${encodeURIComponent(token)}`
    );
    socketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setProgressMessages((prev) => [...prev, payload.message]);
      } catch {
        // Ignore malformed frames.
      }
    };

    const cleanup = () => {
      socket.close();
      socketRef.current = null;
    };

    socket.onopen = async () => {
      try {
        const result = await api.analyze(token, selectedGroup, analysisId);
        cleanup();
        navigate("/report", { state: { analysis: result } });
      } catch (err) {
        cleanup();
        setRunError(err instanceof ApiError ? err.message : "Analysis failed.");
        setIsRunning(false);
      }
    };

    socket.onerror = () => {
      setRunError("Could not connect to the live progress channel.");
    };
  };

  return (
    <div className="page">
      <h1>Run a Cost Analysis</h1>
      <p className="page-subtitle">
        Select an Azure resource group and let AI scan it for cost optimization opportunities.
      </p>

      {loadingGroups && <p>Loading resource groups...</p>}
      {loadError && <p className="form-error">{loadError}</p>}

      {!loadingGroups && !loadError && (
        <div className="dashboard-controls">
          <label>
            Resource Group
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              disabled={isRunning}
            >
              {resourceGroups.length === 0 && <option value="">No resource groups found</option>}
              {resourceGroups.map((group) => (
                <option key={group.name} value={group.name}>
                  {group.name} ({group.location})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={runAnalysis}
            disabled={isRunning || !selectedGroup}
          >
            {isRunning ? "Running Analysis..." : "Run Analysis"}
          </button>
        </div>
      )}

      {(progressMessages.length > 0 || runError) && (
        <div className="progress-panel">
          <h2>Progress</h2>
          <ProgressTracker messages={progressMessages} error={runError} />
        </div>
      )}
    </div>
  );
}
