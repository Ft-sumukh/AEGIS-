"use client";

import { useEffect, useState, useRef } from "react";
import { LiveOperationalEvent } from "@/lib/api/types";

interface UseLiveEventsOptions {
  companyId?: string;
  onEvent?: (event: LiveOperationalEvent) => void;
  maxStored?: number;
}

export function useLiveEvents(options: UseLiveEventsOptions = {}) {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<LiveOperationalEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<LiveOperationalEvent | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    let es: EventSource | null = null;
    let isMounted = true;

    const connect = () => {
      try {
        const url = options.companyId
          ? `/api/v1/stream/events?company_id=${options.companyId}`
          : `/api/v1/stream/events`;

        es = new EventSource(url);

        es.onopen = () => {
          if (isMounted) setConnected(true);
        };

        es.onerror = () => {
          if (isMounted) {
            setConnected(false);
            if (es) {
              es.close();
              es = null;
            }
            // Reconnect after 5 seconds
            reconnectTimeoutRef.current = setTimeout(connect, 5000);
          }
        };

        es.onmessage = (event) => {
          try {
            const data: LiveOperationalEvent = JSON.parse(event.data);
            if (isMounted) {
              setLastEvent(data);
              setEvents((prev) => [data, ...prev.slice(0, (optionsRef.current.maxStored || 25) - 1)]);
              if (optionsRef.current.onEvent) {
                optionsRef.current.onEvent(data);
              }
            }
          } catch {
            // Heartbeat or malformed frame
          }
        };

        // Also listen to named event channels
        const eventChannels = [
          "ANOMALY_DETECTED",
          "INCIDENT_CREATED",
          "INCIDENT_RESOLVED",
          "INCIDENT_MITIGATED",
          "ACTION_APPROVED",
          "ACTION_EXECUTED",
          "ACTION_VERIFIED",
          "CHAOS_FAULT_INJECTED",
          "CHAOS_FAULT_RECOVERED",
        ];

        eventChannels.forEach((channel) => {
          es?.addEventListener(channel, (e: MessageEvent) => {
            try {
              const data: LiveOperationalEvent = JSON.parse(e.data);
              if (isMounted) {
                setLastEvent(data);
                setEvents((prev) => [data, ...prev.slice(0, (optionsRef.current.maxStored || 25) - 1)]);
                if (optionsRef.current.onEvent) {
                  optionsRef.current.onEvent(data);
                }
              }
            } catch {
              // Ignore parse error
            }
          });
        });
      } catch {
        if (isMounted) {
          setConnected(false);
          reconnectTimeoutRef.current = setTimeout(connect, 5000);
        }
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (es) es.close();
    };
  }, [options.companyId]);

  return { connected, events, lastEvent };
}
