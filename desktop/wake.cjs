const { spawn } = require('node:child_process');
const path = require('node:path');
class WakeListener {
  constructor({ root, onWake, onInterrupt = () => {}, onStatus, onDiagnostics = () => {}, onTestComplete = () => {}, spawnProcess = spawn }) {
    Object.assign(this, { root, onWake, onInterrupt, onStatus, onDiagnostics, onTestComplete, spawnProcess });
    this.child = null;
    this.stopping = Promise.resolve();
    this.failed = false;
  }
  start({ test = false, interrupt = false, threshold = 0.70 } = {}) {
    if (this.child || this.failed) return;
    const args = ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', path.join(this.root, 'desktop', 'Wake-AIRA.ps1'), '-ConfidenceThreshold', String(threshold), '-TestSeconds', test ? '20' : '0'];
    if (interrupt) args.push('-InterruptMode');
    const status = value => this.onStatus(interrupt ? 'interrupt:' + value : value);
    const child = this.spawnProcess('powershell.exe', args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], env: process.env });
    this.child = child;
    this.mode = interrupt ? 'interrupt' : test ? 'test' : 'wake';
    status('starting');
    let buffer = '';
    child.stdout.on('data', data => {
      buffer += data.toString();
      let end;
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, end).trim(); buffer = buffer.slice(end + 1);
        if (child !== this.child) continue;
        if (line === 'READY') status('listening');
        if (line.startsWith('DIAG:')) {
          try {
            const value = JSON.parse(line.slice(5));
            const phrases = ['hey aira', 'hey eye ra', 'hey ira', 'hey ayra', 'hey air ah', 'hey eye rah', 'hey aura', 'hey era'];
            this.onDiagnostics({
              level: Math.max(0, Math.min(100, Number(value.level) || 0)),
              speechCount: Math.max(0, Number(value.speechCount) || 0),
              rejectedCount: Math.max(0, Number(value.rejectedCount) || 0),
              phrase: phrases.includes(value.phrase) ? value.phrase : '',
              confidence: Math.max(0, Math.min(1, Number(value.confidence) || 0)),
              matched: value.matched === true,
              signal: String(value.signal || '').replace(/[^a-zA-Z]/g, '').slice(0, 60),
              culture: /^[a-z]{2}-[A-Z]{2}$/.test(value.culture) ? value.culture : '',
            });
          } catch {} // Ignore malformed diagnostics; never forward arbitrary recognition text.
        }
        if (line === 'INTERRUPT' && interrupt && !test) { void this.stop(); this.onInterrupt(); break; }
        if (line === 'WAKE' && !test && !interrupt) { void this.stop().then(() => this.onWake()); break; }
        if (line === 'DONE' && test) { void this.stop().then(() => this.onTestComplete()); break; }
        if (line.startsWith('ERROR:')) { this.failed = true; status(line); }
      }
    });
    child.stderr.on('data', () => {}); // Do not echo system diagnostics or personal audio.
    child.on('error', () => { if (child !== this.child) return; this.child = null; this.failed = true; status('ERROR:Could not start Windows speech recognition.'); });
    child.on('exit', () => {
      if (child === this.child) {
        this.child = null;
        if (!this.failed) status('ERROR:Wake listener stopped. Disable and re-enable to retry.');
        this.failed = true;
      }
    });
  }
  async stop() {
    const child = this.child;
    if (!child) return this.stopping;
    this.child = null;
    this.mode = null;
    this.stopping = new Promise(resolve => {
      child.once('exit', resolve);
      child.once('close', resolve);
      child.once('error', resolve);
      child.kill();
    });
    await this.stopping;
  }
  retry() { this.failed = false; }
}
module.exports = { WakeListener };
