import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Navbar from "./components/Navbar";
import SignupPage from "./pages/SignupPage";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ReportPage from "./pages/ReportPage";
import HistoryPage from "./pages/HistoryPage";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navbar />
        <main>
          <Routes>
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/report"
              element={
                <ProtectedRoute>
                  <ReportPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/history"
              element={
                <ProtectedRoute>
                  <HistoryPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
