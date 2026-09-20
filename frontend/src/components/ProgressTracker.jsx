export default function ProgressTracker({ messages = [], error }) {
  if (messages.length === 0 && !error) {
    return null;
  }

  const failed = (msg) => msg.toLowerCase().startsWith("analysis failed");

  return (
    <ul className="progress-tracker">
      {messages.map((message, index) => (
        <li
          key={`${index}-${message}`}
          className={`progress-step ${failed(message) ? "failed" : "done"}`}
          style={{ animationDelay: `${index * 60}ms` }}
        >
          <span className="progress-icon">{failed(message) ? "✕" : "✓"}</span>
          <span className="progress-message">{message}</span>
        </li>
      ))}
      {error && !messages.some(failed) && (
        <li className="progress-step failed" style={{ animationDelay: `${messages.length * 60}ms` }}>
          <span className="progress-icon">✕</span>
          <span className="progress-message">{error}</span>
        </li>
      )}
    </ul>
  );
}
