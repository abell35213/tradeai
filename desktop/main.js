const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const waitOn = require("wait-on");

const BACKEND_PORT = 5055;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}/health`;
const FRONTEND_DEV_URL = "http://localhost:3000"; // React dev server

let backendProc = null;

function startBackend() {
  // Adjust python executable if needed:
  // - "python3" is typical on mac
  // - if you use venv, point to that python
  const pythonExe = process.env.TRADEAI_PYTHON || "python3";

  const backendPath = path.join(__dirname, "..", "backend", "app.py");

  backendProc = spawn(pythonExe, [backendPath], {
    env: { ...process.env, TRADEAI_PORT: String(BACKEND_PORT) },
    stdio: "inherit"
  });

  backendProc.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
  });
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    webPreferences: {
      // Keep this simple for v1 (no preload/IPC needed yet)
      contextIsolation: true
    }
  });

  // Wait for backend health
  await waitOn({
    resources: [BACKEND_URL],
    timeout: 30000
  });

  // In v1, load React dev server (run `npm start` in frontend separately)
  await win.loadURL(FRONTEND_DEV_URL);
}

app.whenReady().then(async () => {
  startBackend();
  await createWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (backendProc) backendProc.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProc) backendProc.kill();
});

