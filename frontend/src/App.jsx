import { useEffect, useMemo, useState } from "react";
import { completeUpload, downloadUrl, getJob, getLogs, startJob, startUpload, uploadChunk } from "./api.js";
import { Sun, Moon, FileText, BookOpen, Terminal, User, Upload, Download, X, RefreshCw, Copy, Check, Github, Mail, AlertTriangle, Zap, Star, Gem, Package, Minimize, Eye, Search, ArrowRight, Sliders, Settings, ChevronDown, ChevronUp } from "./icons.jsx";

const MB = 1024 * 1024;
const VER = "1.0.0";
const fmt = (v) => !v && v !== 0 ? "-" : v < MB ? `${v} B` : v < MB * 1024 ? `${(v / MB).toFixed(1)} MB` : `${(v / (MB * 1024)).toFixed(2)} GB`;

/* ---- Theme ---- */
function useTheme() {
  const [t, setT] = useState(() => { try { return localStorage.getItem("pdf-studio-theme") || "dark"; } catch { return "dark"; } });
  useEffect(() => { document.documentElement.setAttribute("data-theme", t); try { localStorage.setItem("pdf-studio-theme", t); } catch {} }, [t]);
  return [t, () => setT(p => p === "dark" ? "light" : "dark")];
}

/* ================================================================
   Log Viewer
   ================================================================ */
function LogViewer({ onClose }) {
  const [entries, setEntries] = useState([]);
  const [sys, setSys] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const fetch_ = async () => { setLoading(true); try { const d = await getLogs(300); setEntries(d.entries || []); setSys(d.system || null); } catch { setEntries([{ ts: "", level: "ERROR", source: "ui", message: "Failed to fetch" }]); } setLoading(false); };
  useEffect(() => { fetch_(); }, []);

  const txt = useMemo(() => {
    const s = sys ? [`=== System ===`, `CPU: ${sys.cpu_count}`, `Tesseract: ${sys.tesseract_cmd} (${sys.tesseract_exists})`, `DPI: ${sys.ocr_dpi}`, `Lang: ${sys.ocr_lang}`, "", `=== Logs ===`] : [];
    return [...s, ...entries.map(e => `[${e.ts}] [${e.level}] [${e.source}]${e.job_id ? ` [${e.job_id.slice(0, 8)}]` : ""} ${e.message}`)].join("\n");
  }, [entries, sys]);

  const cp = async () => { try { await navigator.clipboard.writeText(txt); } catch { const a = document.createElement("textarea"); a.value = txt; document.body.appendChild(a); a.select(); document.execCommand("copy"); document.body.removeChild(a); } setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-panel">
        <div className="modal-header">
          <h2><Terminal size={18} /> Application Logs</h2>
          <div className="modal-actions">
            <button className="modal-btn" onClick={fetch_}><RefreshCw size={13} /> Refresh</button>
            <button className="modal-btn" onClick={cp}>{copied ? <><Check size={13} /> Copied</> : <><Copy size={13} /> Copy</>}</button>
            <button className="modal-btn modal-close" onClick={onClose}><X size={13} /></button>
          </div>
        </div>
        {sys && <div className="sys-info-bar"><span>CPU: <strong>{sys.cpu_count} cores</strong></span><span>Tesseract: <strong>{sys.tesseract_exists ? "Yes" : "No"}</strong></span><span>DPI: <strong>{sys.ocr_dpi}</strong></span><span>Lang: <strong>{sys.ocr_lang}</strong></span></div>}
        <div className="modal-body">
          {loading ? <p className="log-empty">Loading...</p> : entries.length === 0 ? <p className="log-empty">No log entries yet. Run a job to generate logs.</p> : (
            <div className="log-list">{entries.map((e, i) => (
              <div key={i} className={`log-row ${e.level === "ERROR" ? "is-error" : ""}`}>
                <span className="log-ts">{e.ts}</span>
                <span className={`log-lv ${e.level.toLowerCase()}`}>{e.level}</span>
                <span className="log-src">{e.source}</span>
                {e.job_id && <span className="log-jid">{e.job_id.slice(0, 8)}</span>}
                <span className="log-message">{e.message}</span>
              </div>
            ))}</div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   Documentation
   ================================================================ */
function DocsPanel({ onClose }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-panel">
        <div className="modal-header">
          <h2><BookOpen size={18} /> User Manual</h2>
          <div className="modal-actions"><button className="modal-btn modal-close" onClick={onClose}><X size={13} /></button></div>
        </div>
        <div className="modal-body docs">
          <h3><Zap size={16} /> Quick Start</h3>
          <p>PDF Studio is a unified local PDF toolkit. Select a tool from the sidebar, upload a PDF, and process it — all locally on your machine.</p>
          <ol>
            <li><span className="doc-step-num">1</span><strong>Select a Tool</strong> — Choose OCR or Compress from the sidebar</li>
            <li><span className="doc-step-num">2</span><strong>Upload a PDF</strong> — Click the upload area or drag a file (up to 1 GB)</li>
            <li><span className="doc-step-num">3</span><strong>Configure</strong> — Choose quality preset or compression level</li>
            <li><span className="doc-step-num">4</span><strong>Process</strong> — Click Start and monitor progress</li>
            <li><span className="doc-step-num">5</span><strong>Download</strong> — Get your processed PDF</li>
          </ol>

          <h3><Search size={16} /> OCR Tool</h3>
          <p>Converts scanned PDFs into searchable documents using Tesseract OCR.</p>
          <table><thead><tr><th>Preset</th><th>DPI</th><th>Speed</th><th>Best For</th></tr></thead><tbody>
            <tr><td><strong>Fast</strong></td><td>200</td><td>Fastest</td><td>Quick previews, drafts</td></tr>
            <tr><td><strong>Standard</strong></td><td>300</td><td>~1.5-2x</td><td>Daily use (recommended)</td></tr>
            <tr><td><strong>Maximum</strong></td><td>400</td><td>~3-4x</td><td>Archival, print-ready</td></tr>
          </tbody></table>
          <div className="doc-callout"><strong>Pro Tip:</strong> Standard and Maximum modes use a text-overlay technique that preserves original image quality perfectly.</div>

          <h3><Minimize size={16} /> Compress Tool</h3>
          <p>Compresses PDFs by re-encoding images and recompressing streams. Handles files up to 1 GB+.</p>
          <table><thead><tr><th>Preset</th><th>Image Quality</th><th>Description</th></tr></thead><tbody>
            <tr><td><strong>Lossless</strong></td><td>100%</td><td>Recompress streams only — zero quality loss</td></tr>
            <tr><td><strong>Balanced</strong></td><td>JPEG Q85</td><td>Downsample &gt;150 DPI, strip metadata</td></tr>
            <tr><td><strong>Maximum</strong></td><td>JPEG Q60</td><td>Aggressive downsample &gt;120 DPI</td></tr>
            <tr><td><strong>Custom</strong></td><td>You choose</td><td>Full control: quality, DPI, grayscale, metadata</td></tr>
          </tbody></table>
          <div className="doc-callout"><strong>Pro Tip:</strong> Text in PDFs is vector-based and always stays at maximum quality — only images are affected by compression settings. Use Custom mode for fine-grained control.</div>

          <h3><Package size={16} /> How It Works</h3>
          <ul>
            <li><strong>Chunked Upload</strong> — Large files split into 8 MB chunks for reliable transfer</li>
            <li><strong>Parallel OCR</strong> — Multiple Tesseract processes across all CPU cores</li>
            <li><strong>Stream Recompression</strong> — Re-deflate all PDF streams at maximum level</li>
            <li><strong>Image Deduplication</strong> — Find and merge identical images</li>
            <li><strong>100% Local</strong> — No files ever leave your machine</li>
          </ul>

          <h3><AlertTriangle size={16} /> Troubleshooting</h3>
          <ul>
            <li><strong>OCR is slow</strong> — Use Fast preset, or close CPU-heavy applications</li>
            <li><strong>Tesseract not found</strong> — Check Logs panel; verify installation path</li>
            <li><strong>Compression minimal</strong> — Already-optimized PDFs may see small reductions</li>
            <li><strong>Upload fails</strong> — Ensure enough disk space (~3x file size during processing)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   About
   ================================================================ */
function AboutPanel({ onClose }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-panel" style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <h2><User size={18} /> About</h2>
          <div className="modal-actions"><button className="modal-btn modal-close" onClick={onClose}><X size={13} /></button></div>
        </div>
        <div className="modal-body about">
          <div className="about-icon"><User size={28} /></div>
          <p className="about-name">Raja</p>
          <p className="about-handle">@stranger0407</p>
          <p className="about-bio">Full-stack developer building tools that make document processing accessible, efficient, and private. PDF Studio was created to be the one-stop local PDF toolkit — no cloud, no subscriptions, no limits.</p>
          <div className="about-links">
            <a className="about-link" href="https://github.com/stranger0407" target="_blank" rel="noopener noreferrer"><Github size={15} /> GitHub</a>
            <a className="about-link" href="https://github.com/stranger0407/pdf-studio" target="_blank" rel="noopener noreferrer"><Package size={15} /> Source Code</a>
            <a className="about-link" href="mailto:rgjha2001@gmail.com"><Mail size={15} /> rgjha2001@gmail.com</a>
          </div>
          <hr className="about-divider" />
          <p className="about-tagline">Built with ❤️ — 100% local, 100% free</p>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   Shared file upload + status component
   ================================================================ */
function FileUploadCard({ file, setFile, uploadPct }) {
  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };
  return (
    <div className="dropzone" onClick={() => document.getElementById("pdf-input").click()}>
      <label className="dropzone-label" htmlFor="pdf-input">
        <div className="dropzone-icon"><Upload size={20} /></div>
        <div className="dropzone-text">
          <span className="file-name">{file ? file.name : "Choose a PDF file"}</span>
          <span className="file-hint">{file ? fmt(file.size) : "Up to 1 GB supported"}</span>
        </div>
      </label>
      <input id="pdf-input" type="file" accept="application/pdf" onChange={onFile} />
    </div>
  );
}

/* ================================================================
   Main App
   ================================================================ */
export default function App() {
  const [activeTool, setActiveTool] = useState("ocr");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [uploadPct, setUploadPct] = useState(0);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [log, setLog] = useState("Ready to upload a PDF.");

  // OCR-specific
  const [quality, setQuality] = useState("standard");

  // Compress-specific
  const [compressPreset, setCompressPreset] = useState("lossless");
  const [jpegQuality, setJpegQuality] = useState(75);
  const [maxDpi, setMaxDpi] = useState(150);
  const [dpiEnabled, setDpiEnabled] = useState(true);
  const [grayscale, setGrayscale] = useState(false);
  const [stripMetadata, setStripMetadata] = useState(true);

  const [showLogs, setShowLogs] = useState(false);
  const [showDocs, setShowDocs] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [theme, toggleTheme] = useTheme();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const canStart = useMemo(() => file && status !== "uploading" && status !== "processing", [file, status]);

  // Reset state when switching tools
  const switchTool = (tool) => {
    if (tool === activeTool) return;
    setActiveTool(tool);
    setFile(null);
    setStatus("idle");
    setUploadPct(0);
    setJob(null);
    setError("");
    setLog("Ready to upload a PDF.");
    // Reset the file input so the same file can be re-selected
    const inp = document.getElementById("pdf-input");
    if (inp) inp.value = "";
  };

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "error") return;
    const id = job.job_id; let off = false;
    const iv = setInterval(async () => {
      if (off) return;
      try { const u = await getJob(id); if (off) return; setJob(u); setStatus(u.status === "queued" ? "processing" : u.status); if (u.message) setLog(u.message); }
      catch (e) { if (!off && !(e.message || "").toLowerCase().includes("not found")) setError(e.message); }
    }, 2000);
    return () => { off = true; clearInterval(iv); };
  }, [job?.job_id, job?.status]);

  const onFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setError(""); setUploadPct(0); setJob(null); setStatus("idle");
    setFile(f);
    setLog("File selected. Ready to process.");
    // Reset value so selecting the same file again triggers onChange
    e.target.value = "";
  };

  const onStart = async () => {
    if (!file) return; setError(""); setStatus("uploading"); setLog("Starting upload...");
    try {
      const up = await startUpload(file); const cs = up.chunk_size; const tc = Math.ceil(file.size / cs);
      for (let i = 0; i < tc; i++) { await uploadChunk(up.upload_id, i, file.slice(i * cs, Math.min((i + 1) * cs, file.size))); setUploadPct(Math.round((i + 1) / tc * 100)); setLog(`Uploading chunk ${i + 1} of ${tc}`); }
      await completeUpload(up.upload_id); setStatus("processing"); setLog(`Upload complete. Starting ${activeTool === "ocr" ? "OCR" : "compression"}...`);
      setJob(await startJob(up.upload_id, {
        tool: activeTool,
        quality,
        compressPreset,
        jpegQuality: compressPreset === "custom" ? jpegQuality : null,
        maxDpi: compressPreset === "custom" && dpiEnabled ? maxDpi : null,
        grayscale: compressPreset === "custom" ? grayscale : false,
        stripMetadata: compressPreset === "custom" ? stripMetadata : true,
      }));
    } catch (e) { setError(e.message); setStatus("idle"); }
  };

  const dl = job?.status === "done" ? downloadUrl(job.job_id) : null;
  const reportUrl = `mailto:rgjha2001@gmail.com?subject=${encodeURIComponent("PDF Studio — Bug Report")}&body=${encodeURIComponent(`Hi Raja,\n\nI encountered an issue with PDF Studio v${VER}.\n\nTool: ${activeTool}\nError: ${error || "(describe the issue)"}\nFile: ${file?.name || "N/A"}\nPreset: ${activeTool === "ocr" ? quality : compressPreset}\nStatus: ${status}\n\nSteps to reproduce:\n1. \n2. \n3. \n\nThanks!`)}`;

  const tools = [
    { id: "ocr", icon: Search, label: "OCR", desc: "Make PDFs searchable" },
    { id: "compress", icon: Minimize, label: "Compress", desc: "Reduce file size" },
  ];

  return (
    <div className="app-layout">
      {/* ---- Sidebar ---- */}
      <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-icon"><FileText size={22} /></div>
          {!sidebarCollapsed && <div className="brand-text"><h1>PDF Studio</h1><span className="brand-tag">Local PDF Toolkit</span></div>}
        </div>

        <nav className="sidebar-nav">
          <div className="nav-label">{!sidebarCollapsed && "Tools"}</div>
          {tools.map(t => (
            <button
              key={t.id}
              className={`nav-item ${activeTool === t.id ? "active" : ""}`}
              onClick={() => switchTool(t.id)}
              title={t.label}
            >
              <t.icon size={18} />
              {!sidebarCollapsed && <div className="nav-item-text"><span className="nav-item-label">{t.label}</span><span className="nav-item-desc">{t.desc}</span></div>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item" onClick={toggleTheme} title={theme === "dark" ? "Light Mode" : "Dark Mode"}>
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            {!sidebarCollapsed && <span className="nav-item-label">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
          </button>
          <button className="nav-item" onClick={() => setShowDocs(true)} title="Docs"><BookOpen size={18} />{!sidebarCollapsed && <span className="nav-item-label">Docs</span>}</button>
          <button className="nav-item" onClick={() => setShowLogs(true)} title="Logs"><Terminal size={18} />{!sidebarCollapsed && <span className="nav-item-label">Logs</span>}</button>
          <button className="nav-item" onClick={() => setShowAbout(true)} title="About"><User size={18} />{!sidebarCollapsed && <span className="nav-item-label">About</span>}</button>
        </div>
      </aside>

      {/* ---- Main Content ---- */}
      <main className="main-content">
        <div className="tool-header">
          <div className="tool-header-info">
            <h2>{activeTool === "ocr" ? "OCR — Make PDFs Searchable" : "Compress — Reduce File Size"}</h2>
            <p className="tool-subtitle">
              {activeTool === "ocr"
                ? "Convert scanned PDFs into searchable documents — fast, private, and local."
                : "Compress PDFs without quality loss — handles files up to 1 GB and beyond."
              }
            </p>
          </div>
        </div>

        <section className="tool-grid">
          {/* ---- Input Card ---- */}
          <div className="card">
            <div className="card-title">Input</div>

            <div className="dropzone">
              <label className="dropzone-label" htmlFor="pdf-input">
                <div className="dropzone-icon"><Upload size={20} /></div>
                <div className="dropzone-text">
                  <span className="file-name">{file ? file.name : "Choose a PDF file"}</span>
                  <span className="file-hint">{file ? fmt(file.size) : "Up to 1 GB supported"}</span>
                </div>
              </label>
              <input id="pdf-input" type="file" accept="application/pdf" onChange={onFileSelect} />
            </div>

            {/* ---- OCR Quality Presets ---- */}
            {activeTool === "ocr" && (
              <div>
                <div className="quality-label">Quality Preset</div>
                <div className="quality-options">
                  {[["fast", "Fast", "200 DPI", "Quick previews"], ["standard", "Standard", "300 DPI", "Recommended"], ["maximum", "Maximum", "400 DPI", "Archival"]].map(([v, n, d, hint]) => (
                    <label className="quality-option" key={v}>
                      <input type="radio" name="quality" value={v} checked={quality === v} onChange={() => setQuality(v)} />
                      <div className="quality-card">
                        <span className="q-name">{n}</span>
                        <span className="q-detail">{d}</span>
                        <span className="q-hint">{hint}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* ---- Compress Presets ---- */}
            {activeTool === "compress" && (
              <div>
                <div className="quality-label">Compression Level</div>
                <div className="quality-options four-col">
                  {[["lossless", "Lossless", "Zero quality loss", "Stream packing"], ["balanced", "Balanced", "JPEG Q85 · 150 DPI", "Recommended"], ["maximum", "Maximum", "JPEG Q60 · 120 DPI", "Smallest file"], ["custom", "Custom", "You configure", "Advanced"]].map(([v, n, d, hint]) => (
                    <label className="quality-option" key={v}>
                      <input type="radio" name="compress-preset" value={v} checked={compressPreset === v} onChange={() => setCompressPreset(v)} />
                      <div className={`quality-card ${v === "custom" ? "custom-card" : ""}`}>
                        {v === "custom" ? <Sliders size={16} /> : null}
                        <span className="q-name">{n}</span>
                        <span className="q-detail">{d}</span>
                        <span className="q-hint">{hint}</span>
                      </div>
                    </label>
                  ))}
                </div>

                {/* ---- Custom Controls Panel ---- */}
                {compressPreset === "custom" && (
                  <div className="custom-panel">
                    <div className="custom-panel-header">
                      <Settings size={15} />
                      <span>Custom Compression Settings</span>
                    </div>

                    {/* JPEG Quality Slider */}
                    <div className="custom-control">
                      <div className="custom-control-header">
                        <label className="custom-control-label">Image Quality (JPEG)</label>
                        <span className="custom-control-value">{jpegQuality}</span>
                      </div>
                      <input
                        type="range" min="10" max="100" step="5"
                        value={jpegQuality}
                        onChange={e => setJpegQuality(Number(e.target.value))}
                        className="custom-slider"
                      />
                      <div className="custom-slider-labels">
                        <span>10 (Tiny)</span>
                        <span>50</span>
                        <span>100 (Best)</span>
                      </div>
                    </div>

                    {/* Max DPI */}
                    <div className="custom-control">
                      <div className="custom-control-header">
                        <label className="custom-control-label">Max Image DPI</label>
                        <label className="custom-toggle">
                          <input type="checkbox" checked={dpiEnabled} onChange={e => setDpiEnabled(e.target.checked)} />
                          <span className="toggle-track"><span className="toggle-thumb" /></span>
                          <span className="toggle-label">{dpiEnabled ? "Downsample ON" : "Off (keep original)"}</span>
                        </label>
                      </div>
                      {dpiEnabled && (
                        <>
                          <input
                            type="range" min="72" max="600" step="1"
                            value={maxDpi}
                            onChange={e => setMaxDpi(Number(e.target.value))}
                            className="custom-slider"
                          />
                          <div className="custom-slider-labels">
                            <span>72 (Screen)</span>
                            <span>150</span>
                            <span>300 (Print)</span>
                            <span>600</span>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Grayscale Toggle */}
                    <div className="custom-control">
                      <div className="custom-control-header">
                        <label className="custom-control-label">Convert to Grayscale</label>
                        <label className="custom-toggle">
                          <input type="checkbox" checked={grayscale} onChange={e => setGrayscale(e.target.checked)} />
                          <span className="toggle-track"><span className="toggle-thumb" /></span>
                          <span className="toggle-label">{grayscale ? "Yes" : "No"}</span>
                        </label>
                      </div>
                      <p className="custom-hint">Removes color data — great for text-heavy or B&W scanned docs</p>
                    </div>

                    {/* Strip Metadata Toggle */}
                    <div className="custom-control">
                      <div className="custom-control-header">
                        <label className="custom-control-label">Strip Metadata</label>
                        <label className="custom-toggle">
                          <input type="checkbox" checked={stripMetadata} onChange={e => setStripMetadata(e.target.checked)} />
                          <span className="toggle-track"><span className="toggle-thumb" /></span>
                          <span className="toggle-label">{stripMetadata ? "Yes" : "No"}</span>
                        </label>
                      </div>
                      <p className="custom-hint">Removes thumbnails, producer info, and non-essential metadata</p>
                    </div>

                    {/* Summary */}
                    <div className="custom-summary">
                      <strong>Summary:</strong> JPEG Q{jpegQuality}
                      {dpiEnabled ? ` · Max ${maxDpi} DPI` : " · Original DPI"}
                      {grayscale ? " · Grayscale" : ""}
                      {stripMetadata ? " · Strip metadata" : ""}
                    </div>
                  </div>
                )}
              </div>
            )}

            <button className="btn-primary" onClick={onStart} disabled={!canStart}>
              {activeTool === "ocr" ? <><Search size={16} /> Start OCR</> : <><Minimize size={16} /> Start Compression</>}
            </button>

            <div className="progress-wrap">
              <div className="progress-fill" style={{ width: `${uploadPct}%` }} />
              <span className="progress-text">{uploadPct}% uploaded</span>
            </div>
          </div>

          {/* ---- Status Card ---- */}
          <div className="card">
            <div className="card-title">Status</div>
            <div className="status-row">
              <span className={`status-badge ${status}`}>{status}</span>
              {job && <span className="status-badge tool-badge">{job.tool || activeTool}</span>}
              {job && <span className="status-badge">job {job.job_id.slice(0, 8)}</span>}
            </div>
            <p className="status-msg">{log}</p>
            {job && <div className="progress-wrap"><div className="progress-fill" style={{ width: `${job.progress || 0}%` }} /><span className="progress-text">{job.progress || 0}% processed</span></div>}

            {/* Compression result summary */}
            {dl && activeTool === "compress" && job?.input_size && (
              <div className="compress-result">
                <div className="compress-result-row">
                  <div className="compress-stat">
                    <span className="compress-stat-label">Original</span>
                    <span className="compress-stat-value">{fmt(job.input_size)}</span>
                  </div>
                  <ArrowRight size={18} />
                  <div className="compress-stat">
                    <span className="compress-stat-label">Compressed</span>
                    <span className="compress-stat-value accent">{fmt(job.output_size)}</span>
                  </div>
                  <div className="compress-stat">
                    <span className="compress-stat-label">Saved</span>
                    <span className="compress-stat-value success">{job.reduction_pct}%</span>
                  </div>
                </div>
              </div>
            )}

            {dl && (
              <a className="btn-link" href={dl}>
                <Download size={16} />
                {activeTool === "ocr" ? "Download Searchable PDF" : "Download Compressed PDF"}
              </a>
            )}
            {error && (
              <div>
                <p className="error-text">{error}</p>
                <a className="ctrl-btn" href={reportUrl} style={{ marginTop: 8, display: "inline-flex", textDecoration: "none", color: "var(--error)" }}>
                  <AlertTriangle size={14} /> Report Error
                </a>
              </div>
            )}
          </div>
        </section>

        {/* ---- Footer ---- */}
        <footer className="footer">
          <p>Built by <strong>Raja</strong></p>
          <div className="footer-links">
            <a href="https://github.com/stranger0407" target="_blank" rel="noopener noreferrer"><Github size={13} /> GitHub</a>
            <a href="https://github.com/stranger0407/pdf-studio" target="_blank" rel="noopener noreferrer"><Package size={13} /> Source</a>
            <a href="mailto:rgjha2001@gmail.com"><Mail size={13} /> Contact</a>
            <a href={reportUrl}><AlertTriangle size={13} /> Report Bug</a>
          </div>
          <span className="version">v{VER}</span>
        </footer>
      </main>

      {showLogs && <LogViewer onClose={() => setShowLogs(false)} />}
      {showDocs && <DocsPanel onClose={() => setShowDocs(false)} />}
      {showAbout && <AboutPanel onClose={() => setShowAbout(false)} />}
    </div>
  );
}
