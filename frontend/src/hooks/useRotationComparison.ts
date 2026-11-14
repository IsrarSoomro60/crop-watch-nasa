import { useState } from "react";
import { api } from "../services/api";
import type { ComparisonRequest, Recommendation } from "../types";

export function useRotationComparison() {
  const [data, setData] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function compare(body: ComparisonRequest) {
    setLoading(true);
    setError(null);
    try {
      setData(await api.compareRotations(body));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return { data, error, loading, compare };
}
