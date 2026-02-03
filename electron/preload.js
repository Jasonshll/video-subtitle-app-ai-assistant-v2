const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  
  // 可以根据需要添加更多 API
  openDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
  saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options)
});
