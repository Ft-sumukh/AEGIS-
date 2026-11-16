"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UsePollingOptions {
  intervalSeconds?: number;
  enabled?: boolean;
}

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  options: UsePollingOptions = {}
) {
  const { intervalSeconds = 30, enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [secondsAgo, setSecondsAgo] = useState<number>(0);
  const [activeInterval, setActiveInterval] = useState<number | null>(
    enabled ? intervalSeconds : null
  );

  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  const executeFetch = useCallback(async (isManual: boolean = false) => {
    if (isManual) {
      setIsRefreshing(true);
    }
    try {
      const result = await fetchFnRef.current();
      setData(result);
      setError(null);
      setLastUpdated(new Date());
      setSecondsAgo(0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    executeFetch();
  }, [executeFetch]);

  // Polling timer
  useEffect(() => {
    if (activeInterval === null || activeInterval <= 0) return;

    const timer = setInterval(() => {
      executeFetch();
    }, activeInterval * 1000);

    return () => clearInterval(timer);
  }, [activeInterval, executeFetch]);

  // Second-counter ticker for "Updated X seconds ago"
  useEffect(() => {
    const ticker = setInterval(() => {
      setSecondsAgo(Math.round((Date.now() - lastUpdated.getTime()) / 1000));
    }, 1000);

    return () => clearInterval(ticker);
  }, [lastUpdated]);

  const refresh = useCallback(() => {
    return executeFetch(true);
  }, [executeFetch]);

  const setIntervalValue = useCallback((val: number | null) => {
    setActiveInterval(val);
  }, []);

  return {
    data,
    error,
    isLoading,
    isRefreshing,
    lastUpdated,
    secondsAgo,
    activeInterval,
    setIntervalValue,
    refresh,
  };
}
