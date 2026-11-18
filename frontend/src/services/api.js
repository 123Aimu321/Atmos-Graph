
const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep the HTTP error message.
    }

    throw new Error(message);
  }

  return response.json();
}

export const api = {
  getGraph: () => request("/api/graph"),

  getEntities: () => request("/api/entities"),

  getScenarios: () => request("/api/scenarios"),

  getMetrics: () => request("/api/model/metrics"),

  getRipple: (nodeId) =>
  request(`/api/ripple/${encodeURIComponent(nodeId)}`),

  predict: (disruptedNode) =>
    request("/api/predict", {
      method: "POST",
      body: JSON.stringify({
        disrupted_node: disruptedNode,
      }),
    }),

    analyzeEvent: (text) =>
  request("/api/analyze-event", {
    method: "POST",
    body: JSON.stringify({ text }),
  }), 

  assessRisk: (prediction, ripple, disruptionType = "OTHER") =>
  request("/api/risk-assessment", {
    method: "POST",
    body: JSON.stringify({
      prediction,
      ripple,
      disruption_type: disruptionType,
    }),
  }),


downloadImpactReport: async (payload) => {
  const baseUrl =
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000";

  const response = await fetch(
    `${baseUrl}/api/reports/impact`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(
      `Report generation failed: ${response.status}`
    );
  }

  return response.blob();
},

saveImpact: (incidentId, prediction) =>
  request(`/api/impacts/${incidentId}`, {
    method: "POST",
    body: JSON.stringify({ prediction }),
  }),

getImpact: (incidentId) =>
  request(`/api/impacts/${incidentId}`),

predictDelay: (
  nodeId,
  initialDelayDays = 14,
  decay = 0.75
) =>
  request("/api/delay/predict", {
    method: "POST",
    body: JSON.stringify({
      disrupted_node: nodeId,
      initial_delay_days: initialDelayDays,
      decay,
    }),
  }),

getDelayMetrics: () =>
  request("/api/delay/metrics"),

predictForecast: (
  nodeId,
  initialDelayDays = 14,
  recoveryHalfLifeDays = 30
) =>
  request("/api/forecast/predict", {
    method: "POST",
    body: JSON.stringify({
      disrupted_node: nodeId,
      initial_delay_days: initialDelayDays,
      decay: 0.75,
      recovery_half_life_days: recoveryHalfLifeDays,
    }),
  }),
  

saveHistory: (incidentId, payload) =>
  request(
    `/api/history/incidents/${encodeURIComponent(
      incidentId
    )}/snapshots`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  ),

getHistory: (incidentId, limit = 50) =>
  request(
    `/api/history/incidents/${encodeURIComponent(
      incidentId
    )}/snapshots?limit=${limit}`
  ),

getHistorySnapshot: (snapshotId) =>
  request(
    `/api/history/snapshots/${encodeURIComponent(
      snapshotId
    )}`
  ),

};
