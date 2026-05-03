const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const BACKEND_PORT = 8000;
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`;

let backendProcess = null;
let appQuitting = false;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getLogPath() {
  const logDir = path.join(app.getPath("userData"), "logs");
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  return path.join(logDir, "backend.log");
}

function resolveVendorDir() {
  if (app.isPackaged) {
    const packagedVendor = path.join(process.resourcesPath, "vendor");
    if (fs.existsSync(packagedVendor)) {
      return packagedVendor;
    }
    return null;
  }
  const devVendor = path.join(__dirname, "vendor");
  return fs.existsSync(devVendor) ? devVendor : null;
}

function findTesseractCmd(vendorDir) {
  if (!vendorDir) {
    return null;
  }
  const direct = path.join(vendorDir, "tesseract.exe");
  if (fs.existsSync(direct)) {
    return direct;
  }
  const nested = path.join(vendorDir, "tesseract", "tesseract.exe");
  if (fs.existsSync(nested)) {
    return nested;
  }
  return null;
}

function buildBackendEnv() {
  const env = { ...process.env };
  const dataDir = path.join(app.getPath("userData"), "data");
  env.APP_DATA_DIR = dataDir;

  const vendorDir = resolveVendorDir();
  if (vendorDir) {
    env.PATH = `${vendorDir};${env.PATH || ""}`;
    const tesseractCmd = findTesseractCmd(vendorDir);
    if (tesseractCmd) {
      env.TESSERACT_CMD = tesseractCmd;
    }
  }

  return env;
}

function resolveBackendCommand() {
  if (app.isPackaged) {
    const exePath = path.join(process.resourcesPath, "backend", "pdf-studio-backend.exe");
    return {
      command: exePath,
      args: [],
      cwd: path.dirname(exePath),
    };
  }

  const python = process.env.BACKEND_PYTHON || "python";
  const backendDir = path.resolve(__dirname, "..", "backend");
  return {
    command: python,
    args: [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(BACKEND_PORT),
    ],
    cwd: backendDir,
  };
}

function startBackend() {
  const backend = resolveBackendCommand();
  const env = buildBackendEnv();

  const logPath = getLogPath();
  const logFd = fs.openSync(logPath, "a");
  fs.appendFileSync(logPath, `\n--- Backend starting at ${new Date().toISOString()} ---\n`);
  fs.appendFileSync(logPath, `Command: ${backend.command}\n`);
  fs.appendFileSync(logPath, `Args: ${JSON.stringify(backend.args)}\n`);
  fs.appendFileSync(logPath, `CWD: ${backend.cwd}\n`);
  fs.appendFileSync(logPath, `Exists: ${fs.existsSync(backend.command)}\n\n`);

  backendProcess = spawn(backend.command, backend.args, {
    cwd: backend.cwd,
    env,
    stdio: ["ignore", logFd, logFd],
    windowsHide: true,
  });

  backendProcess.on("error", (err) => {
    fs.appendFileSync(logPath, `Spawn error: ${err.message}\n`);
    if (!appQuitting) {
      dialog.showErrorBox(
        "PDF Studio",
        `Failed to start backend: ${err.message}`
      );
      app.quit();
    }
  });

  backendProcess.on("exit", (code) => {
    fs.appendFileSync(logPath, `Backend exited with code: ${code}\n`);
    if (appQuitting) {
      return;
    }
    const message = `Backend exited unexpectedly (code ${code ?? "unknown"}).\nCheck log: ${logPath}`;
    dialog.showErrorBox("PDF Studio", message);
    app.quit();
  });
}

async function waitForBackend() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(HEALTH_URL, { method: "GET" });
      if (response.ok) {
        return;
      }
    } catch {
      // ignore until backend is ready
    }
    await sleep(500);
  }
  throw new Error("Backend failed to start. Check that Tesseract is available.");
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    autoHideMenuBar: true,
    title: "PDF Studio",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const devUrl = process.env.ELECTRON_DEV_SERVER_URL;
  if (devUrl) {
    win.loadURL(devUrl);
    return;
  }

  const indexPath = app.isPackaged
    ? path.join(process.resourcesPath, "renderer", "index.html")
    : path.join(__dirname, "..", "frontend", "dist", "index.html");
  win.loadFile(indexPath);
}

function stopBackend() {
  if (!backendProcess) {
    return;
  }
  try {
    backendProcess.kill();
  } catch {
    // process may already be dead
  }
  backendProcess = null;
}

app.whenReady().then(async () => {
  try {
    startBackend();
    await waitForBackend();
    createWindow();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown startup error";
    dialog.showErrorBox("PDF Studio", message);
    app.quit();
  }
});

app.on("before-quit", () => {
  appQuitting = true;
  stopBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
