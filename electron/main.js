const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');

let mainWindow;
let pythonProcess = null;
let isQuitting = false;

// 强制终止 Python 进程的函数
function killPythonProcess() {
  if (pythonProcess) {
    console.log('Killing Python process...');
    
    // Windows 上强制终止进程树
    if (process.platform === 'win32') {
      try {
        // 使用 taskkill 强制终止进程树
        exec(`taskkill /pid ${pythonProcess.pid} /T /F`, (err) => {
          if (err) {
            console.log('taskkill error (process may already be dead):', err.message);
          } else {
            console.log('Python process killed via taskkill');
          }
        });
      } catch (e) {
        console.error('Error killing process:', e);
      }
    }
    
    // 同时发送 kill 信号
    try {
      pythonProcess.kill('SIGTERM');
      setTimeout(() => {
        if (pythonProcess && !pythonProcess.killed) {
          pythonProcess.kill('SIGKILL');
        }
      }, 2000);
    } catch (e) {
      console.error('Error sending kill signal:', e);
    }
    
    pythonProcess = null;
  }
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: '阿泽字幕助手',
    icon: path.join(__dirname, '../backend/app_icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: false // 开发时允许跨域
    },
    show: false, // 准备完成后再显示
    frame: false, // 无边框窗口
    backgroundColor: '#00000000', // 透明背景
    titleBarStyle: 'hidden' // macOS 下隐藏标题栏但保留控制按钮（可选，这里统一用 frame: false）
  });

  // 窗口控制事件
  ipcMain.on('window-minimize', () => {
    mainWindow.minimize();
  });

  ipcMain.on('window-maximize', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });

  ipcMain.on('window-close', () => {
    mainWindow.close();
  });

  // 加载前端页面
  const isDev = process.argv.includes('--dev');
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }

  // 窗口准备好后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // 处理窗口关闭
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      // 如果不是真正退出，可以在这里处理一些清理工作
    }
  });
}

// 启动 Python 后端
function startPythonBackend() {
  const isDev = process.argv.includes('--dev');
  let backendPath;
  let args = [];

  if (isDev) {
    // 开发环境：运行 python app.py
    backendPath = 'python';
    args = [path.join(__dirname, '../backend/app.py')];
  } else {
    // 生产环境：运行打包后的可执行文件
    backendPath = path.join(process.resourcesPath, 'backend', '阿泽字幕助手-后端.exe');
  }

  console.log('Starting backend at:', backendPath, args);

  try {
    pythonProcess = spawn(backendPath, args, {
      cwd: isDev ? path.join(__dirname, '../backend') : path.join(process.resourcesPath, 'backend'),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
      if (!isQuitting) {
        // 后端异常退出，可以在这里通知前端
      }
    });
  } catch (e) {
    console.error('Failed to start backend:', e);
  }
}

// 应用生命周期
app.whenReady().then(() => {
  startPythonBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    isQuitting = true;
    killPythonProcess();
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  killPythonProcess();
});
