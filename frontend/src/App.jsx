/**
 * @file Root application component: quantum background stack, page
 * transitions, layout shell and the single app-level WebSocket connection
 * feeding the Zustand store.
 */
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import { Route, Routes, useLocation } from 'react-router-dom';
import useWebSocket from './hooks/useWebSocket.js';
import QuantumBackground from './components/background/QuantumBackground.jsx';
import QuantumCursor from './components/effects/QuantumCursor.jsx';
import ErrorBoundary from './components/common/ErrorBoundary.jsx';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import AboutPage from './pages/AboutPage.jsx';
import AttackSimulatorPage from './pages/AttackSimulatorPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import LogsPage from './pages/LogsPage.jsx';

/** Fade + slide wrapper for routed pages. */
function PageShell({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Render the app layout with navigation, animated page routes, and the live
 * stream.
 */
export default function App() {
  useWebSocket(); // one connection for the entire app
  const location = useLocation();

  return (
    <ErrorBoundary>
      <div className="relative min-h-screen">
        <QuantumBackground />
        <QuantumCursor />
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'rgba(19, 19, 46, 0.9)',
              color: '#fff',
              border: '1px solid rgba(0, 240, 255, 0.3)',
              backdropFilter: 'blur(12px)',
              fontFamily: 'Outfit, sans-serif',
            },
          }}
        />
        <Header />
        <div className="relative z-10 flex">
          <Sidebar />
          <main className="min-w-0 flex-1 p-6">
            <AnimatePresence mode="wait">
              <Routes location={location} key={location.pathname}>
                <Route path="/" element={<PageShell><DashboardPage /></PageShell>} />
                <Route path="/attacks" element={<PageShell><AttackSimulatorPage /></PageShell>} />
                <Route path="/logs" element={<PageShell><LogsPage /></PageShell>} />
                <Route path="/about" element={<PageShell><AboutPage /></PageShell>} />
              </Routes>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
