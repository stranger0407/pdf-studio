const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // ignore json parse errors
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export async function startUpload(file) {
  return request(`${API_BASE}/uploads/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: file.name, total_size: file.size }),
  });
}

export async function uploadChunk(uploadId, index, blob) {
  return request(`${API_BASE}/uploads/${uploadId}/chunk?index=${index}`, {
    method: "PUT",
    headers: { "Content-Type": "application/octet-stream" },
    body: blob,
  });
}

export async function completeUpload(uploadId) {
  return request(`${API_BASE}/uploads/${uploadId}/complete`, {
    method: "POST",
  });
}

export async function startJob(uploadId, {
  tool = "ocr",
  quality = "standard",
  compressPreset = "lossless",
  jpegQuality = null,
  maxDpi = null,
  grayscale = false,
  stripMetadata = true,
  textColor = null,
  bgColor = null,
} = {}) {
  const body = {
    upload_id: uploadId,
    tool,
    quality,
    compress_preset: compressPreset,
  };
  // Only include custom params when using custom preset
  if (compressPreset === "custom") {
    body.jpeg_quality = jpegQuality;
    body.max_dpi = maxDpi;
    body.grayscale = grayscale;
    body.strip_metadata = stripMetadata;
  }
  // Include restyle params
  if (tool === "restyle") {
    body.text_color = textColor;
    body.bg_color = bgColor;
  }
  return request(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getJob(jobId) {
  return request(`${API_BASE}/jobs/${jobId}`);
}

export function downloadUrl(jobId) {
  return `${API_BASE}/jobs/${jobId}/download`;
}

export async function getLogs(tail = 200) {
  return request(`${API_BASE}/logs?tail=${tail}`);
}
