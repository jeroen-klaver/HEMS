/**
 * useHistory — fetches historical time-series data from GET /api/v1/history.
 *
 * Re-fetches whenever `range` changes.
 * Returns the response data, a loading flag, and an error string.
 */

import { useEffect, useState } from "react";
import type { HistoryResponse } from "../types";

type Range = "1h" | "6h" | "24h" | "7d" | "30d";

interface HistoryState {
  data: HistoryResponse | null;
  loading: boolean;
  error: string | null;
}

export function useHistory(range: Range): HistoryState {
  const [state, setState] = useState<HistoryState>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    setState({ data: null, loading: true, error: null });

    fetch(`/api/v1/history?range=${range}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HistoryResponse>;
      })
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setState({ data: null, loading: false, error: String(err) });
      });

    return () => {
      cancelled = true;
    };
  }, [range]);

  return state;
}
