/**
 * App — root component with routing and persistent shell layout.
 *
 * Shell:
 *   - Top nav bar: logo + nav links + live connection dot
 *   - Page content area
 */

import { NavLink, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { useLiveData } from "./hooks/useLiveData";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Pricing from "./pages/Pricing";
import Settings from "./pages/Settings";

const NAV_LINKS = [
  { to: "/",         label: "Dashboard" },
  { to: "/history",  label: "History" },
  { to: "/pricing",  label: "Pricing" },
  { to: "/settings", label: "Settings" },
];

function ConnectionDot() {
  const { connected } = useLiveData();
  return (
    <span
      className={`w-2 h-2 rounded-full flex-shrink-0 ${connected ? "bg-green-500" : "bg-amber-400 animate-pulse"}`}
      title={connected ? "Live" : "Reconnecting…"}
    />
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Nav bar */}
      <header className="border-b border-slate-800 px-4 py-3 flex items-center gap-6">
        <span className="font-bold text-white tracking-tight">⚡ HEMS</span>

        <nav className="flex gap-1 flex-1">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-slate-700 text-white font-medium"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <ConnectionDot />
      </header>

      {/* Page content */}
      <main className="flex-1 px-4 py-6 max-w-5xl w-full mx-auto">
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Shell>
        <Routes>
          <Route path="/"         element={<Dashboard />} />
          <Route path="/history"  element={<History />} />
          <Route path="/pricing"  element={<Pricing />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Shell>
    </Router>
  );
}
