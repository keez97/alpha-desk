import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { MorningBrief } from './pages/MorningBrief';
import { Screener } from './pages/Screener';
import { WeeklyReport } from './pages/WeeklyReport';
import { Portfolio } from './pages/Portfolio';
import { RRG } from './pages/RRG';
import { Backtester } from './pages/Backtester';
import { Events } from './pages/Events';
import { Earnings } from './pages/Earnings';
import { Sentiment } from './pages/Sentiment';
import { Confluence } from './pages/Confluence';
import { Correlation } from './pages/Correlation';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt: number) => Math.min(2000 * 2 ** attempt, 15000),
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,    // 5 minutes - don't re-fetch if data is fresh
      gcTime: 30 * 60 * 1000,      // 30 minutes - keep cached data around
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<MorningBrief />} />
            <Route path="/morning-brief" element={<MorningBrief />} />
            <Route path="/screener" element={<Screener />} />
            <Route path="/weekly-report" element={<WeeklyReport />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/rrg" element={<RRG />} />
            <Route path="/backtester" element={<Backtester />} />
            <Route path="/events" element={<Events />} />
            <Route path="/earnings" element={<Earnings />} />
            <Route path="/sentiment" element={<Sentiment />} />
            <Route path="/confluence" element={<Confluence />} />
            <Route path="/correlation" element={<Correlation />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
