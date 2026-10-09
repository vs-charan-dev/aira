const { contextBridge, ipcRenderer } = require('electron');
const listen = (channel, callback) => {
  const handler = (_event, value) => callback(value);
  ipcRenderer.on(channel, handler);
  return () => ipcRenderer.removeListener(channel, handler);
};
// Narrow capabilities only; renderers never receive Node, filesystem, or shell access.
contextBridge.exposeInMainWorld('airaDesktop', {
  role: process.argv.includes('--aira-overlay') ? 'overlay' : process.argv.includes('--aira-board') ? 'board' : 'owner',
  ready: () => ipcRenderer.send('aira:ready'),
  prepareAudio: () => ipcRenderer.invoke('aira:prepare-audio'),
  screenSource: () => ipcRenderer.invoke('aira:screen-source'),
  screenSnapshot: () => ipcRenderer.invoke('aira:screen-snapshot'),
  publish: state => ipcRenderer.send('aira:state', state),
  configure: config => ipcRenderer.invoke('aira:configure', config),
  testWake: () => ipcRenderer.invoke('aira:test-wake'),
  runAction: (action, requestId) => ipcRenderer.invoke('aira:run-action', action, requestId),
  stopAction: requestId => ipcRenderer.invoke('aira:stop-action', requestId),
  listApps: () => ipcRenderer.invoke('aira:list-apps'),
  showPalace: () => ipcRenderer.send('aira:show-palace'),
  showTasks: () => ipcRenderer.send('aira:show-tasks'),
  showInvoiceDemo: () => ipcRenderer.invoke('aira:show-invoice-demo'),
  command: command => ipcRenderer.send('aira:command', command),
  onCommand: callback => listen('aira:command', callback),
  onState: callback => listen('aira:state', callback),
  onHost: callback => listen('aira:host', callback),
  onCursor: callback => listen('aira:cursor', callback),
});
