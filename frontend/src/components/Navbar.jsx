import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <Link to="/" className="brand">
        ☁️ AI Cloud Cost Detective
      </Link>
      <div className="nav-links">
        {isAuthenticated ? (
          <>
            <Link to="/">Dashboard</Link>
            <Link to="/history">History</Link>
            <span className="nav-user">{user?.email}</span>
            <button type="button" onClick={handleLogout} className="link-button">
              Log out
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Sign up</Link>
          </>
        )}
      </div>
    </nav>
  );
}
