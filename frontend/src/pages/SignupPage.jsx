import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [secret, setSecret] = useState("");
  const [confirmSecret, setConfirmSecret] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (secret !== confirmSecret) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await signup(email, secret);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Signup failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Create your account</h1>
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            required
            minLength={8}
            value={confirmSecret}
            onChange={(e) => setConfirmSecret(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Creating account..." : "Sign up"}
        </button>
        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
