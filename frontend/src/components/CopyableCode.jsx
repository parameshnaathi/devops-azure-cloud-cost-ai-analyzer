import { useState } from "react";

export default function CopyableCode({ command }) {
  const [copied, setCopied] = useState(false);

  if (!command) {
    return null;
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      // Clipboard API can be unavailable (e.g. insecure context); ignore silently.
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="copyable-code">
      <pre>
        <code>{command}</code>
      </pre>
      <button type="button" onClick={handleCopy} className="copy-button">
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}
