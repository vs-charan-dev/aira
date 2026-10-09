const { app, BrowserWindow, Menu, Tray, nativeImage, globalShortcut, ipcMain, screen, powerMonitor, dialog, desktopCapturer } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const { WakeListener } = require('./wake.cjs');
const { DesktopActions } = require('./actions.cjs');
const { selectScreen } = require('./screen-source.cjs');
const root = path.resolve(process.env.AIRA_ROOT || path.join(__dirname, '..'));
const smoke = process.argv.includes('--smoke-test');
const base = process.env.AIRA_URL || 'http://127.0.0.1:8000';
const url = new URL(base);
if (url.hostname !== '127.0.0.1' || url.protocol !== 'http:') throw new Error('AIRA desktop requires the loopback backend.');
const cache = path.join(root, '.cache', 'desktop');
fs.mkdirSync(cache, { recursive: true });
// Set before ready/Chromium startup so profiles, sessions, logs, dumps stay on E.
app.setPath('userData', path.join(cache, 'profile'));
app.setPath('sessionData', path.join(cache, 'session'));
app.setPath('logs', path.join(cache, 'logs'));
app.setPath('crashDumps', path.join(cache, 'crash-dumps'));
const exportsDir=path.join(root,'data','exports');
fs.mkdirSync(exportsDir,{recursive:true});
app.setPath('downloads',exportsDir);
app.commandLine.appendSwitch('disk-cache-dir', path.join(cache, 'http-cache'));
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
const configFile = path.join(root, 'data', 'desktop', 'settings.json');
let config = { hotkey: 'Control+Alt+A', wakeEnabled: false, wakeSensitivity: 'normal', controlEnabled: true };
try { config = { ...config, ...JSON.parse(fs.readFileSync(configFile, 'utf8')) }; } catch {}
let owner, overlay, taskBoard, tray, ready = false, quitting = false, suspended = false;
let state = { mood: 'idle', label: 'Ready', busy: false, energy: 0, hiddenUntil: 0 };
let host = { hotkey: config.hotkey, hotkeyRegistered: false, wakeEnabled: config.wakeEnabled, wakeStatus: 'disabled', wakeSensitivity: config.wakeSensitivity === 'sensitive' ? 'sensitive' : 'normal', wakeTesting: false, wakeDiagnostic: null, wakeTestResult: '' };
let wakeTimer;
let wakeTestMatched = false;
let wakeTestBest = null;
let wakeRequest = 0;
let recognizerMode = 'idle';
host.interruptStatus = 'paused';
const smokeReactErrors = [];
host.controlEnabled = config.controlEnabled !== false;
host.stopHotkeyRegistered = false;
host.desktopAction = null;
let actionLabelUntil = 0;
function overlayState() {
  const action = host.desktopAction;
  if (action?.running || (action && Date.now() < actionLabelUntil)) return { ...state, mood: ['speaking','listening','capturing'].includes(state.mood) ? state.mood : action.running ? 'thinking' : action.status === 'failed' ? 'error' : state.mood, label: action.label, busy: state.busy || action.running, hiddenUntil: 0 };
  return state;
}
const actions = new DesktopActions({ root, onState: value => {
  const wasRunning = host.desktopAction?.running;
  host.desktopAction = value; actionLabelUntil = value.running ? 0 : Date.now() + 8000;
  broadcastHost(); send(overlay, 'aira:state', overlayState());
  if (wasRunning !== value.running) reconcileWake();
} });
function stopDesktop() { actions.stop(); }
function emergencyStop() { stopDesktop(); command({ action: 'switch_mode', mode: 'stop' }); }
const pixels = Buffer.alloc(32 * 32 * 4);
for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) {
  if (Math.hypot(x - 16, y - 16) > 15) continue;
  let color = [239, 103, 52, 255]; // BGRA
  if (((x - 10) / 5) ** 2 + ((y - 14) / 7) ** 2 < 1 || ((x - 22) / 5) ** 2 + ((y - 14) / 7) ** 2 < 1) color = [255, 255, 255, 255];
  if (Math.hypot(x - 11, y - 14) < 3 || Math.hypot(x - 23, y - 14) < 3) color = [66, 36, 20, 255];
  color.forEach((value, index) => { pixels[(y * 32 + x) * 4 + index] = value; });
}
const icon = nativeImage.createFromBitmap(pixels, { width: 32, height: 32 });
const send = (win, channel, value) => { if (win && !win.isDestroyed() && !win.webContents.isDestroyed()) win.webContents.send(channel, value); };
function broadcastHost() {
  host.wakeEnabled = config.wakeEnabled;
  send(owner, 'aira:host', host); send(overlay, 'aira:host', host);
  if (tray) tray.setToolTip(`AIRA • ${host.wakeStatus === 'listening' ? 'Hey AIRA enabled' : host.wakeStatus} • ${config.hotkey}`);
}
const wake = new WakeListener({ root,
  onInterrupt: () => { if (!suspended && !quitting && (state.busy || host.desktopAction?.running)) emergencyStop(); },
  onWake: () => { if (config.wakeEnabled && !state.busy && !host.wakeTesting) void activate(); },
  onStatus: status => {
    if (status.startsWith('interrupt:')) host.interruptStatus = status.slice(10);
    else { host.wakeStatus = status; if (status.startsWith('ERROR:') && host.wakeTesting) { host.wakeTesting = false; host.wakeTestResult = status; } }
    broadcastHost();
  },
  onDiagnostics: value => {
    if (recognizerMode === 'interrupt') return;
    host.wakeDiagnostic = value;
    if (host.wakeTesting) {
      if (value.matched) wakeTestMatched = true;
      if (value.phrase && (!wakeTestBest || value.confidence > wakeTestBest.confidence)) wakeTestBest = value;
    }
    broadcastHost();
  },
  onTestComplete: () => {
    if (!host.wakeTesting) return;
    host.wakeTesting = false;
    const diagnostic = host.wakeDiagnostic;
    const score = wakeTestBest ? `Best match: “${wakeTestBest.phrase}” at ${Math.round(wakeTestBest.confidence * 100)}%. ` : '';
    host.wakeTestResult = score + (wakeTestMatched ? 'Wake phrase matched. Enabled wake listening resumes; otherwise choose Enable Hey AIRA.' : wakeTestBest ? 'Below the confidence cutoff. Try More sensitive and test again.' : diagnostic?.speechCount ? 'Speech detected, but the wake phrase was rejected. Try saying Hey eye-rah or Hey air-ah.' : 'No speech detected. Check Windows Sound → Input and its microphone test.');
    reconcileWake();
  },
});
function reconcileWake() {
  clearTimeout(wakeTimer);
  if (!smoke && ready && !suspended && !quitting && (state.busy || host.desktopAction?.running)) {
    host.wakeTesting = false;
    host.wakeStatus = config.wakeEnabled ? 'paused' : 'disabled';
    if (wake.mode === 'interrupt' && wake.child) { broadcastHost(); return; }
    recognizerMode = 'interrupt'; host.interruptStatus = 'starting';
    const request = ++wakeRequest; broadcastHost();
    wakeTimer = setTimeout(async () => {
      await wake.stop();
      if (request !== wakeRequest || suspended || quitting || (!state.busy && !host.desktopAction?.running)) return;
      wake.retry(); wake.start({ interrupt: true, threshold: 0.80 });
    }, 100);
    return;
  }
  recognizerMode = 'idle'; host.interruptStatus = 'paused';
  if (host.wakeTesting && !smoke && ready && !suspended && !quitting && !state.busy && !host.desktopAction?.running) return;
  if (host.wakeTesting) { host.wakeTesting = false; host.wakeTestResult = 'Wake test cancelled.'; }
  if (smoke || !ready || suspended || quitting || state.busy || host.desktopAction?.running || !config.wakeEnabled) {
    wakeRequest++;
    void wake.stop();
    host.wakeStatus = config.wakeEnabled ? 'paused' : 'disabled'; broadcastHost();
    return;
  }
  // Let queued output end before rearming, avoiding the assistant waking itself.
  const request = ++wakeRequest;
  host.wakeStatus = 'starting'; broadcastHost();
  wakeTimer = setTimeout(async () => {
    // Await the previous microphone process exit before opening another one.
    await wake.stop();
    if (request !== wakeRequest || suspended || quitting || state.busy || host.desktopAction?.running || !config.wakeEnabled) return;
    host.wakeDiagnostic = null;
    wake.start({ threshold: config.wakeSensitivity === 'sensitive' ? 0.55 : 0.70 });
  }, 1800);
}
function command(value) { send(owner, 'aira:command', value); }
async function activate() {
  if (!ready || suspended || quitting) return;
  const request = ++wakeRequest;
  clearTimeout(wakeTimer);
  if (host.wakeTesting) { host.wakeTesting = false; host.wakeTestResult = 'Wake test cancelled by activation.'; }
  await wake.stop();
  if (request !== wakeRequest || suspended || quitting) return;
  wake.retry();
  host.wakeStatus = config.wakeEnabled ? 'paused' : 'disabled'; broadcastHost();
  overlay?.showInactive();
  command({ action: 'activate' });
}
function showPalace() { owner.show(); owner.focus(); }
function place() {
  const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  const area = display.workArea;
  const width = Math.min(340, area.width), height = Math.min(260, area.height);
  overlay.setBounds({ x: area.x + Math.round((area.width - width) / 2), y: area.y + area.height - height, width, height });
}
function guardWindow(win) {
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event, target) => {
    if (new URL(target).origin !== url.origin) event.preventDefault();
  });
}
function setHotkey(hotkey) {
  if (/^(Control|Ctrl)\+Alt\+(Escape|Esc)$/i.test(hotkey)) throw new Error('Ctrl+Alt+Escape is reserved for stopping AIRA.');
  if (typeof hotkey !== 'string' || hotkey.length > 80 || !/(Control|Ctrl|Alt|Shift|Super)/i.test(hotkey)) throw new Error('Use a modifier key, for example Control+Alt+A.');
  if (host.hotkeyRegistered) globalShortcut.unregister(config.hotkey);
  config.hotkey = hotkey;
  try { host.hotkeyRegistered = globalShortcut.register(hotkey, () => void activate()); } catch { host.hotkeyRegistered = false; }
  host.hotkey = hotkey;
  broadcastHost();
}
function authorized(event, role = 'owner') {
  return event.sender === (role === 'owner' ? owner?.webContents : overlay?.webContents) && event.senderFrame?.url?.startsWith(url.origin + '/');
}
function showTasks() {
  if (taskBoard && !taskBoard.isDestroyed()) { taskBoard.show(); taskBoard.focus(); return; }
  const area = screen.getDisplayNearestPoint(screen.getCursorScreenPoint()).workArea;
  taskBoard = new BrowserWindow({ width: 420, height: Math.min(780, area.height), x: area.x + 12, y: area.y + 12, title: 'AIRA · Tasks', alwaysOnTop: true,
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true, backgroundThrottling: false, additionalArguments: ['--aira-board'] } });
  guardWindow(taskBoard);
  taskBoard.on('closed', () => { taskBoard = null; });
  void taskBoard.loadURL(base + '/tasks');
}
async function showInvoiceDemo(requestId) {
  taskBoard?.hide();
  return actions.run({kind:'show_invoice_demo',url:base + '/invoice-demo'},requestId);
}
if (!app.requestSingleInstanceLock()) app.exit(smoke ? 2 : 0);
else {
  app.on('second-instance', showPalace);
  app.whenReady().then(async () => {
    if(!smoke && config.controlEnabled !== false) actions.warm();
    const webPreferences = { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true, backgroundThrottling: false };
    owner = new BrowserWindow({ width: 1180, height: 800, show: !smoke, title: 'AIRA · Memory Palace', icon, webPreferences: { ...webPreferences, additionalArguments: ['--aira-owner'] } });
    overlay = new BrowserWindow({ width: 340, height: 260, frame: false, transparent: true, hasShadow: false, resizable: false, skipTaskbar: true, alwaysOnTop: true, focusable: false, show: false, webPreferences: { ...webPreferences, additionalArguments: ['--aira-overlay'] } });
    guardWindow(owner); guardWindow(overlay);
    owner.webContents.session.on('will-download',(_event,item) => {
      const source=new URL(item.getURL());
      if(source.origin===url.origin && source.pathname.startsWith('/media/youtube/')) {
        const filename=path.basename(item.getFilename()).replace(/[^a-zA-Z0-9_.-]/g,'_');
        item.setSavePath(path.join(exportsDir,Date.now()+'-'+filename));
      }
    });
    if (smoke) owner.webContents.on('console-message', (...args) => {
      for (const value of args) {
        const message = typeof value === 'string' ? value : value?.message;
        const code = message?.match(/Minified React error #\d+|Maximum update depth exceeded/);
        if (code) smokeReactErrors.push(code[0]);
      }
    });
    // Overlay is a view only: no microphone, camera, or screen permissions.
    owner.webContents.session.setPermissionCheckHandler((contents, permission, origin) => contents === owner.webContents && origin === url.origin && ['media', 'display-capture', 'speaker-selection'].includes(permission));
    owner.webContents.session.setPermissionRequestHandler((contents, permission, callback) => callback(contents === owner.webContents && contents.getURL().startsWith(url.origin + '/') && ['media', 'display-capture', 'speaker-selection'].includes(permission)));
    overlay.setIgnoreMouseEvents(true, { forward: true });
    overlay.setAlwaysOnTop(true, 'screen-saver');
    place();
    overlay.once('ready-to-show', () => { if (!smoke) overlay.showInactive(); });
    owner.on('close', event => { if (!quitting) { event.preventDefault(); owner.hide(); } });
    owner.webContents.on('render-process-gone', () => { ready = false; stopDesktop(); void wake.stop(); host.wakeStatus = 'ERROR:Palace stopped. Restart AIRA.'; broadcastHost(); });
    tray = new Tray(icon);
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: 'Activate AIRA', click: () => void activate() },
      { label: 'Open Memory Palace', click: showPalace },
      { label: 'Show task board', click: showTasks },
      { label: 'Stop all actions · Ctrl+Alt+Escape', click: emergencyStop },
      { label: 'Stop conversation and capture', click: emergencyStop },
      { label: 'Pause all microphones', click: () => { configure({ wakeEnabled: false }); command({ action: 'switch_mode', mode: 'stop' }); } },
      { label: 'Toggle Hey AIRA', click: () => configure({ wakeEnabled: !config.wakeEnabled }) },
      { label: 'Show character', click: () => command({ action: 'show' }) },
      { type: 'separator' }, { label: 'Quit AIRA', click: () => app.quit() },
    ]));
    tray.on('double-click', showPalace);
    setHotkey(config.hotkey);
    host.stopHotkeyRegistered = globalShortcut.register('Control+Alt+Escape', emergencyStop);
    screen.on('display-metrics-changed', place); screen.on('display-added', place); screen.on('display-removed', place);
    powerMonitor.on('suspend', () => { suspended = true; stopDesktop(); reconcileWake(); command({ action: 'switch_mode', mode: 'stop' }); });
    powerMonitor.on('lock-screen', () => { suspended = true; stopDesktop(); reconcileWake(); command({ action: 'switch_mode', mode: 'stop' }); });
    const resume = () => { suspended = false; place(); reconcileWake(); };
    powerMonitor.on('resume', resume); powerMonitor.on('unlock-screen', resume);
    setInterval(() => {
      if (!overlay.isDestroyed()) {
        const cursor = screen.getCursorScreenPoint(), bounds = overlay.getBounds();
        send(overlay, 'aira:cursor', { x: cursor.x - bounds.x, y: cursor.y - bounds.y });
      }
    }, 80);
    ipcMain.on('aira:ready', event => {
      if (authorized(event)) { ready = true; reconcileWake(); }
      broadcastHost(); send(overlay, 'aira:state', overlayState());
    });
    ipcMain.handle('aira:prepare-audio', async event => { if (!authorized(event)) throw new Error('Only the palace owns audio.'); ++wakeRequest; clearTimeout(wakeTimer); host.wakeTesting = false; await wake.stop(); host.wakeStatus = 'paused'; broadcastHost(); if (state.busy) reconcileWake(); });
    ipcMain.on('aira:state', (event, value) => {
      if (!authorized(event) || !value || typeof value.busy !== 'boolean') return;
      const wasBusy = state.busy;
      state = { mood: ['idle','listening','thinking','capturing','speaking','error'].includes(value.mood) ? value.mood : 'idle', label: String(value.label || '').slice(0, 150), busy: value.busy, energy: Math.max(0, Math.min(1, Number(value.energy) || 0)), hiddenUntil: Number(value.hiddenUntil) || 0 };
      send(overlay, 'aira:state', overlayState());
      if (wasBusy !== state.busy) reconcileWake();
    });
    ipcMain.on('aira:command', (event, value) => {
      if (!authorized(event, 'overlay') || !['activate','show','switch_mode'].includes(value?.action)) return;
      if (value.action === 'activate') void activate();
      else if (value.action === 'show') command({ action: 'show' });
      else if (value.mode === 'stop') command({ action: 'switch_mode', mode: 'stop' });
    });
    ipcMain.on('aira:show-palace', event => { if (authorized(event) || authorized(event, 'overlay')) showPalace(); });
    ipcMain.handle('aira:configure', (event, value) => { if (!authorized(event)) throw new Error('Only the palace can change settings.'); return configure(value); });
    ipcMain.handle('aira:list-apps', event => { if (!authorized(event)) throw new Error('Only the palace can inspect apps.'); return actions.listApps(); });
    ipcMain.on('aira:show-tasks', event => { if (authorized(event) || authorized(event, 'overlay')) showTasks(); });
    ipcMain.handle('aira:show-invoice-demo', async event => {
      const board = event.sender === taskBoard?.webContents && event.senderFrame?.url === url.origin + '/tasks';
      if (!authorized(event) && !board) throw new Error('Only AIRA can open its demo window.');
      if (suspended || quitting || smoke) throw new Error('Unlock Windows and start AIRA before opening the demo.');
      if (config.controlEnabled === false) throw new Error('Enable desktop actions first.');
      const result = await showInvoiceDemo();
      if (result.status !== 'succeeded') throw new Error(result.message);
    });
    ipcMain.handle('aira:run-action', async (event, value, requestId) => {
      if (!authorized(event)) throw new Error('Only the palace can request desktop actions.');
      if (!ready || suspended || quitting || smoke || config.controlEnabled === false) return { status: 'failed', message: 'Desktop actions unavailable. Enable them under Desktop and unlock Windows.' };
      if (requestId !== undefined && (typeof requestId !== 'string' || !/^[a-zA-Z0-9-]{1,80}$/.test(requestId))) return { status: 'failed', message: 'Invalid action request.' };
      if (!host.stopHotkeyRegistered) return { status: 'failed', message: 'Ctrl+Alt+Escape is unavailable. Restart AIRA after freeing this stop shortcut.' };
      if (value?.kind === 'show_invoice_demo') {
        return showInvoiceDemo(requestId);
      }
      return actions.run(value, requestId);
    });
    ipcMain.handle('aira:stop-action', (event, requestId) => { if (!authorized(event)) throw new Error('Only the palace can stop desktop actions.'); actions.stop(typeof requestId === 'string' ? requestId : undefined); });
    ipcMain.handle('aira:test-wake', async event => {
      if (!authorized(event)) throw new Error('Only the palace can test wake recognition.');
      if (!ready || state.busy || host.desktopAction?.running || suspended || quitting || smoke) throw new Error('Stop conversation / capture and desktop actions before testing wake recognition.');
      const request = ++wakeRequest;
      clearTimeout(wakeTimer); host.wakeTesting = false;
      await wake.stop();
      if (request !== wakeRequest || state.busy || host.desktopAction?.running || suspended || quitting) throw new Error('Wake test cancelled by another action. Stop conversation / capture, then retry.');
      host.wakeTesting = true; wakeTestMatched = false; wakeTestBest = null; host.wakeDiagnostic = null; host.wakeTestResult = ''; wake.retry();
      wake.start({ test: true, threshold: config.wakeSensitivity === 'sensitive' ? 0.55 : 0.70 });
      broadcastHost(); return host;
    });
    ipcMain.handle('aira:screen-source', async event => {
      if (!authorized(event)) throw new Error('Only the palace can capture.');
      if (!ready || suspended || quitting || smoke) throw new Error('Screen capture unavailable. Unlock Windows and start AIRA.');
      const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
      const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 0, height: 0 } });
      return selectScreen(sources, display.id).id;
    });
    ipcMain.handle('aira:screen-snapshot', async event => {
      if (!authorized(event)) throw new Error('Only the palace can view the screen.');
      if (!ready || !state.busy || suspended || quitting || smoke) throw new Error('Start a conversation before requesting a screen view.');
      const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
      const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1600, height: 1000 } });
      if (!state.busy || suspended || quitting) throw new Error('Screen request stopped.');
      const thumbnail = selectScreen(sources, display.id).thumbnail;
      if (thumbnail.isEmpty()) throw new Error('The screen could not be captured.');
      return thumbnail.toJPEG(80).toString('base64');
    });
    await Promise.all([owner.loadURL(base + (smoke ? '/character' : '/palace')), overlay.loadURL(base + '/desktop-overlay')]);
    if (smoke) {
      try {
        // React/RAF visual checks need an active compositor, even with backgroundThrottling disabled.
        owner.show(); owner.focus(); overlay.showInactive();
        await overlay.webContents.insertCSS('.aira-native-face, .aira-body { animation: none !important; }');
        const deadline = Date.now() + 5000;
        let result;
        do {
          result = await overlay.webContents.executeJavaScript(`({ character: !!document.querySelector('svg.aira-character'), transparent: getComputedStyle(document.body).backgroundColor, viewOnly: !!window.airaDesktop && window.airaDesktop.role === 'overlay' })`);
          if (result.character && result.transparent === 'rgba(0, 0, 0, 0)') break;
          await new Promise(resolve => setTimeout(resolve, 50));
        } while (Date.now() < deadline);
        await owner.webContents.executeJavaScript(`window.airaDesktop.publish({mood:'capturing',label:'Screen capture on · offline preview',busy:false,energy:.5,hiddenUntil:0})`);
        await new Promise(resolve => setTimeout(resolve, 250));
        result.captureState = await overlay.webContents.executeJavaScript(`!!document.querySelector('.aira-character--capturing') && document.querySelector('[role="status"]').textContent.includes('Screen capture on')`);
        const overlayBounds = overlay.getBounds(), workArea = screen.getDisplayMatching(overlayBounds).workArea;
        result.bottomCentered = Math.abs(overlayBounds.x + overlayBounds.width/2 - workArea.x - workArea.width/2) <= 1 && overlayBounds.y + overlayBounds.height === workArea.y + workArea.height;
        await overlay.webContents.executeJavaScript(`window.dispatchEvent(new PointerEvent('pointermove',{clientX:1500,clientY:50}))`);
        await owner.webContents.executeJavaScript(`window.airaDesktop.publish({mood:'speaking',label:'Speaking · offline check',busy:false,energy:.2,hiddenUntil:0})`);
        await overlay.webContents.capturePage(undefined, { stayHidden: true, stayAwake: true });
        await new Promise(resolve => setTimeout(resolve,900));
        result.viewerGaze = await overlay.webContents.executeJavaScript(`(() => { const pupils = Array.from(document.querySelectorAll('g[transform]')).filter(g => /^translate\\([^)]*\\)$/.test(g.getAttribute('transform'))); return pupils.length === 2 && pupils.every(g => g.getAttribute('transform').slice(10,-1).split(' ').map(Number).every(v => Math.abs(v)<.5)); })()`);
        await fs.promises.writeFile(path.join(cache, 'smoke.json'), JSON.stringify({ ...result, hotkeyRegistered: host.hotkeyRegistered, bounds: overlay.getBounds(), profile: app.getPath('userData'), session: app.getPath('sessionData') }, null, 2));
        await fs.promises.writeFile(path.join(root, '.cache', 'screenshots', 'aira-desktop-overlay.png'), (await overlay.webContents.capturePage(undefined, { stayHidden: true, stayAwake: true })).toPNG());
        // Validate normal startup/auth/one voice-owner renderer without activating Live.
        await owner.loadURL(base + '/palace');
        const ownerDeadline = Date.now() + 10000;
        while (!ready && Date.now() < ownerDeadline) await new Promise(resolve => setTimeout(resolve, 50));
        result.ownerReady = ready && new URL(owner.webContents.getURL()).pathname === '/palace';
        result.ownerControls = await owner.webContents.executeJavaScript(`!!document.querySelector('.aira-desktop-controls')`);
        result.screenViewBridge = await owner.webContents.executeJavaScript(`typeof window.airaDesktop.screenSnapshot === 'function'`);
        result.screenViewGuard = await owner.webContents.executeJavaScript(`window.airaDesktop.screenSnapshot().then(() => false, error => error.message.includes('Start a conversation'))`);
        result.desktopStatusSeparated = await owner.webContents.executeJavaScript(`document.querySelector('.aira-desktop-controls summary')?.textContent.includes('Controls ') && document.querySelector('.aira-desktop-controls summary')?.textContent.includes('Hey AIRA')`);
        const preferences = { controlEnabled: config.controlEnabled, wakeEnabled: config.wakeEnabled };
        stopDesktop();
        result.stopPreservesPreferences = config.controlEnabled === preferences.controlEnabled && config.wakeEnabled === preferences.wakeEnabled;
        result.desktopActions = await owner.webContents.executeJavaScript(`!!document.querySelector('[aria-label="AIRA desktop actions"]') && typeof window.airaDesktop.runAction === 'function' && typeof window.airaDesktop.stopAction === 'function'`);
        result.notionControls = await owner.webContents.executeJavaScript(`!!document.querySelector('[aria-label="Notion note title"]') && !!document.querySelector('[aria-label="Notion note content"]') && Array.from(document.querySelectorAll('button')).some(button => button.textContent.includes('Create private Notion note'))`);
        result.windowsUseControls = await owner.webContents.executeJavaScript(`!!document.querySelector('[aria-label="Windows-Use task"]') && !!document.querySelector('[aria-label="Windows-Use target app"]')`);
        result.windowsUseGuard = await owner.webContents.executeJavaScript(`window.airaDesktop.runAction({kind:'desktop_task',appName:'Notepad',task:'Must not type'}).then(result => result.status === 'failed')`);
        result.notionActionGuard = await owner.webContents.executeJavaScript(`window.airaDesktop.runAction({kind:'create_notion_note',title:'Smoke',content:'Must not be entered'}).then(result => result.status === 'failed')`);
        result.installedApps = await owner.webContents.executeJavaScript(`window.airaDesktop.listApps().then(apps => apps.length > 0 && apps.every(name => typeof name === 'string'))`);
        result.desktopActionGuard = await owner.webContents.executeJavaScript(`window.airaDesktop.runAction({kind:'open_app',appName:'Notion'}).then(result => result.status === 'failed')`);
        result.stopHotkeyRegistered = host.stopHotkeyRegistered;
        result.overlayActionGuard = await overlay.webContents.executeJavaScript(`window.airaDesktop.runAction({kind:'open_app',appName:'Notion'}).then(() => false, error => error.message.includes('Only the palace'))`);
        result.audioControls = await owner.webContents.executeJavaScript(`!!document.querySelector('select[aria-label="AIRA speaker"]')`);
        result.wakeControls = await owner.webContents.executeJavaScript(`!!document.querySelector('select[aria-label="AIRA wake sensitivity"]') && Array.from(document.querySelectorAll('button')).some(button => button.textContent.includes('Test wake phrase')) && typeof window.airaDesktop.testWake === 'function'`);
        result.wakeTestGuard = await owner.webContents.executeJavaScript(`window.airaDesktop.testWake().then(() => false, error => error.message.includes('Stop conversation'))`);
        wake.onDiagnostics({ level: 37, speechCount: 2, rejectedCount: 1, phrase: 'hey eye rah', confidence: .65, matched: false, culture: 'en-US', signal: '' });
        await owner.webContents.capturePage(undefined, { stayHidden: true, stayAwake: true });
        const feedbackDeadline = Date.now() + 5000;
        do {
          result.wakeFeedback = await owner.webContents.executeJavaScript(`document.querySelector('meter')?.value === 37 && document.querySelector('[aria-label="Wake recognition diagnostics"]')?.textContent.includes('65%')`);
          if (result.wakeFeedback) break;
          await new Promise(resolve => setTimeout(resolve, 100));
        } while (Date.now() < feedbackDeadline);
        result.wakeFeedbackDetails = await owner.webContents.executeJavaScript(`({meter:document.querySelector('meter')?.value,summary:document.querySelector('.aira-desktop-controls summary')?.textContent})`);
        // Open real Settings and verify the voice catalogue without generating audio.
        await owner.webContents.executeJavaScript(`document.querySelector('button[aria-label="Open settings"]')?.click()`);
        await owner.webContents.capturePage(undefined, { stayHidden: true, stayAwake: true });
        const voiceDeadline = Date.now() + 15000;
        do {
          result.voiceSettings = await owner.webContents.executeJavaScript(`({ options: document.querySelector('select[aria-label="AIRA voice"]')?.options.length || 0, preview: Array.from(document.querySelectorAll('button')).some(button => button.textContent.includes('Preview “Hi Charan”')), save: Array.from(document.querySelectorAll('button')).some(button => button.textContent === 'Save voice') })`);
          if (result.voiceSettings.options === 30) break;
          await new Promise(resolve => setTimeout(resolve, 100));
        } while (Date.now() < voiceDeadline);
        result.voiceSettings.error = await owner.webContents.executeJavaScript(`document.querySelector('[aria-label="AIRA voice settings"] [role="alert"]')?.textContent || null`);
        result.reactErrors = smokeReactErrors;
        const voiceBounds = await owner.webContents.executeJavaScript(`(() => {
          const section = document.querySelector('[aria-label="AIRA voice settings"]');
          if (!section) return null;
          section.scrollIntoView({block:'center'});
          const bounds = section.getBoundingClientRect();
          return { x: Math.floor(bounds.x), y: Math.floor(bounds.y), width: Math.ceil(bounds.width), height: Math.ceil(bounds.height) };
        })()`);
        if (voiceBounds) {
          // Wake the hidden compositor before capturing the updated modal frame.
          await owner.webContents.capturePage(voiceBounds, { stayHidden: true, stayAwake: true });
          await new Promise(resolve => setTimeout(resolve, 350));
          await fs.promises.writeFile(path.join(root, '.cache', 'screenshots', 'aira-voice-settings.png'), (await owner.webContents.capturePage(voiceBounds, { stayHidden: true, stayAwake: true })).toPNG());
        }
        // Check real Chromium output support without playing sound or acquiring input.
        result.audioOutput = await owner.webContents.executeJavaScript(`(async () => {
          const ctx = new AudioContext();
          try {
            const sinkSelection = typeof ctx.setSinkId === 'function';
            if (sinkSelection) await ctx.setSinkId('');
            await ctx.resume();
            return { sinkSelection, state: ctx.state, sampleRate: ctx.sampleRate };
          } finally { await ctx.close(); }
        })()`);
        await fs.promises.writeFile(path.join(cache, 'smoke.json'), JSON.stringify({ ...result, hotkeyRegistered: host.hotkeyRegistered, bounds: overlay.getBounds(), profile: app.getPath('userData'), session: app.getPath('sessionData') }, null, 2));
        if (!result.screenViewBridge || !result.screenViewGuard || !result.desktopStatusSeparated || !result.stopPreservesPreferences || !result.bottomCentered || !result.viewerGaze || !result.windowsUseControls || !result.windowsUseGuard || !result.character || !result.viewOnly || !result.captureState || !result.ownerReady || !result.ownerControls || !result.desktopActions || !result.notionControls || !result.notionActionGuard || !result.installedApps || !result.desktopActionGuard || !result.overlayActionGuard || !result.stopHotkeyRegistered || !result.audioControls || !result.wakeControls || !result.wakeTestGuard || !result.wakeFeedback || result.voiceSettings.options !== 30 || !result.voiceSettings.preview || !result.voiceSettings.save || result.audioOutput.state !== 'running' || !result.audioOutput.sinkSelection || result.transparent !== 'rgba(0, 0, 0, 0)' || !host.hotkeyRegistered) process.exitCode = 1;
      } catch (error) { console.error(error.message); process.exitCode = 1; }
      app.exit(process.exitCode || 0);
    }
  }).catch(error => { console.error(error.message); app.exit(1); });
}
async function configure(value) {
  if (typeof value?.controlEnabled === 'boolean') { config.controlEnabled = value.controlEnabled; host.controlEnabled = value.controlEnabled; if (!value.controlEnabled) stopDesktop(); else if(!smoke) actions.warm(); }
  if (value?.wakeSensitivity !== undefined && !['normal', 'sensitive'].includes(value.wakeSensitivity)) throw new Error('Choose a valid wake sensitivity.');
  if (typeof value?.hotkey === 'string') setHotkey(value.hotkey);
  if (typeof value?.wakeEnabled === 'boolean' || value?.wakeSensitivity !== undefined) {
    const request = ++wakeRequest;
    if (host.wakeTesting) host.wakeTestResult = 'Wake test cancelled.';
    clearTimeout(wakeTimer); host.wakeTesting = false;
    await wake.stop();
    if (request !== wakeRequest || quitting) return host;
    if (typeof value.wakeEnabled === 'boolean') config.wakeEnabled = value.wakeEnabled;
    if (value.wakeSensitivity !== undefined) config.wakeSensitivity = value.wakeSensitivity;
    host.wakeSensitivity = config.wakeSensitivity === 'sensitive' ? 'sensitive' : 'normal';
    wake.retry(); reconcileWake();
  }
  fs.mkdirSync(path.dirname(configFile), { recursive: true });
  fs.writeFileSync(configFile, JSON.stringify(config, null, 2));
  broadcastHost();
  return host;
}
app.on('before-quit', () => { quitting = true; void actions.shutdown(); clearTimeout(wakeTimer); globalShortcut.unregisterAll(); void wake.stop(); });
app.on('window-all-closed', () => app.quit());
