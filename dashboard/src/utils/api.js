const getBaseUrl = () => {
  const host = window.location.hostname || 'localhost';
  return `http://${host}:8000`;
};

export const API_BASE = getBaseUrl();

export async function fetchDetections(statusFilter = '', severityFilter = '') {
  let url = `${API_BASE}/api/detections?limit=200`;
  if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;
  if (severityFilter) url += `&severity=${encodeURIComponent(severityFilter)}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch detections');
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/api/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function updateDetectionStatus(id, status) {
  const res = await fetch(`${API_BASE}/api/detections/${id}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error('Failed to update detection status');
  return res.json();
}

export async function triggerSimulatedDetection() {
  const res = await fetch(`${API_BASE}/api/sim/trigger`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to trigger simulation');
  return res.json();
}
