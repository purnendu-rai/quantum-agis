/**
 * @file Root application component: layout shell, route table, and the
 * single app-level WebSocket connection feeding the Zustand store.
 */
import { Route, Routes } from 'react-router-dom';
import useWebSocket from './hooks/useWebSocket.js';
import ErrorBoundary from './components/common/ErrorBoundary.jsx';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import AboutPage from './pages/AboutPage.jsx';
import AttackSimulatorPage from './pages/AttackSimulatorPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import LogsPage from './pages/LogsPage.jsx';

/**
 * Render the app layout with navigation, page routes, and the live stream.
 */
export default function App() {
  useWebSocket(); // one connection for the entire app

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-dark-bg">
        <Header />
        <div className="flex">
          <Sidebar />
          <main className="flex-1 p-6">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/attacks" element={<AttackSimulatorPage />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
