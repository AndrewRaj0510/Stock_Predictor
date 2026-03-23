import axios from 'axios';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getAllPredictions(sortBy = 'confidence', horizon = 5) {
  const res = await axios.get(`${BASE}/api/predictions?sort_by=${sortBy}&horizon=${horizon}`);
  return res.data;
}

export async function getPrediction(symbol: string, horizon = 5) {
  const res = await axios.get(`${BASE}/api/predictions/${symbol}?horizon=${horizon}`);
  return res.data;
}

export async function getHistorical(symbol: string, days = 365) {
  const res = await axios.get(`${BASE}/api/historical/${symbol}?days=${days}`);
  return res.data;
}

export async function getFeatures(symbol: string) {
  const res = await axios.get(`${BASE}/api/features/${symbol}`);
  return res.data;
}

export async function getHealth() {
  const res = await axios.get(`${BASE}/api/health`);
  return res.data;
}
