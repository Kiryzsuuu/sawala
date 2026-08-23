import { useEffect, useRef, useState } from "react";
import { WS_URL } from "../api";

const RECONNECT_DELAY_MS = 2000;

export function useWebSocket() {
  const [participants, setParticipants] = useState([]);
  const [lastTimestamp, setLastTimestamp] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer;

    function connect() {
      if (cancelled) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setParticipants(payload.participants || []);
          setLastTimestamp(payload.timestamp);
        } catch (err) {
          console.error("Invalid WS payload", err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  return { participants, lastTimestamp, connected };
}
