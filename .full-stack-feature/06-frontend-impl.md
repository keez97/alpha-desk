# Step 6: Event Scanner Frontend Implementation

## Files Created (9 files)
- `frontend/src/hooks/useEvents.ts` — 8 TanStack Query hooks: useEvents, useEventDetail, useAlphaDecay, useEventTimeline (60s refresh), usePollingStatus, useTriggerScan, useScreenerBadges, useDeleteEvent.
- `frontend/src/pages/Events.tsx` — Two-panel layout: timeline feed (60%) + detail panel (40%).
- `frontend/src/components/events/SeverityBadge.tsx` — Color-coded 1-5 severity (neutral→yellow→orange→red).
- `frontend/src/components/events/EventCard.tsx` — Compact event row with active highlighting.
- `frontend/src/components/events/EventFilters.tsx` — Filter bar: type, severity, date range, ticker.
- `frontend/src/components/events/EventDetail.tsx` — Full detail panel with metadata and delete.
- `frontend/src/components/events/EventTimeline.tsx` — Scrollable list with load-more pagination.
- `frontend/src/components/events/AlphaDecayChart.tsx` — Recharts bar chart: 4 windows, green/red bars.
- `frontend/src/components/events/ScanButton.tsx` — Manual scan trigger + polling status indicator.

## Files Modified
- `frontend/src/lib/api.ts` — Added 5 interfaces + 8 API functions for events
- `frontend/src/App.tsx` — Added /events route
- `frontend/src/components/layout/TopNav.tsx` — Added "Events" nav link
