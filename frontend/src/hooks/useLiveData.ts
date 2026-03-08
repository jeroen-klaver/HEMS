/**
 * useLiveData — subscribes to the backend WebSocket at /ws/live
 * and returns the latest StatusPayload, a connection flag, and an error string.
 *
 * Reconnects automatically with exponential back-off (1s → 2s → 4s … max 30s).
 * Cleans up the socket when the component unmounts.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { StatusPayload } from "../types";

const WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/live`;
const MAX_BACKOFF_MS = 30_000;

interface LiveDataState {
  data: StatusPayload | null;
  connected: boolean;
  error: string | null;
}

export function useLiveData(): LiveDataState {
  const [state, setState] = useState<LiveDataState>({
    data: null,
    connected: false,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef<number>(1000);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      backoffRef.current = 1000; // reset back-off on successful connect
      setState((s) => ({ ...s, connected: true, error: null }));
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data as string) as StatusPayload;
        setState((s) => ({ ...s, data: payload }));
      } catch {
        // Malformed message — ignore
      }
    };

    ws.onerror = () => {
      setState((s) => ({ ...s, error: "WebSocket error" }));
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setState((s) => ({ ...s, connected: false }));
      // Schedule reconnect with back-off
      retryTimerRef.current = setTimeout(() => {
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
        connect();
      }, backoffRef.current);
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return state;
}
