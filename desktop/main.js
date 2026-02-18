const { app, BrowserWindow } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const waitOn = require("wait-on");

const BACKEND_PORT = 5055;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}/health`;
const FRONTEND_DEV_URL = "http://localhost:3000";

const BUILD_DIR = path.join(__dirname, "..", "frontend", "build");
const IS_DEV = process.env.TRADEAI_DEV === "true" || !fs.existsSync(path.join(BUILD_DIR, "index.html"));

let backendProc = null;

function startBackend() {
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
      contextIsolation: true
    }
  });

  await waitOn({
    resources: [BACKEND_URL],
    timeout: 30000
  });

  if (IS_DEV) {
    console.log("Loading from React dev server:", FRONTEND_DEV_URL);
    await win.loadURL(FRONTEND_DEV_URL);
  } else {
    console.log("Loading from build:", BUILD_DIR);
    await win.loadFile(path.join(BUILD_DIR, "index.html"));
  }
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

