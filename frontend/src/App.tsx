import { useEffect, useState } from 'react';
import { 
  Zap,
  Layout
} from 'lucide-react';
import { useStore, wsService } from './store';
import { FileUploader } from './components/FileManager/FileUploader';
import { FileGrid } from './components/FileManager/FileGrid';
import { TaskQueue } from './components/TaskManager/TaskQueue';
import { SettingsModal } from './components/Settings/SettingsModal';
import { SubtitleEditorModal } from './components/SubtitleEditor/SubtitleEditorModal';
import { TitleBar } from './components/Layout/TitleBar';
import { Sidebar } from './components/Layout/Sidebar';
import { apiService } from './services/api';
import './styles/globals.css';

function App() {
  const { 
    tasks,
    isSettingsOpen, 
    setSettingsOpen, 
    isDark,
    isProcessing,
    setConfig
  } = useStore();

  const [isConnected, setIsConnected] = useState(false);

  // 初始化 WebSocket 连接和配置
  useEffect(() => {
    wsService.connect();
    
    const unsubscribe = wsService.on('connection', (data) => {
      const connected = data.status === 'connected';
      setIsConnected(connected);
      
      // 如果重连成功，加入所有正在处理的任务房间
      if (connected) {
        tasks.forEach(task => {
          if (task.status === 'processing') {
            wsService.emitEvent('join_task', { taskId: task.id });
          }
        });
      }
    });

    // 检查 API 健康状态并加载后端配置
    const checkHealth = async () => {
      const healthy = await apiService.healthCheck();
      console.log('API Health:', healthy ? 'OK' : 'Failed');
    };
    checkHealth();

    // 从后端加载配置（确保前后端配置同步）
    const loadBackendConfig = async () => {
      try {
        const backendConfig = await apiService.getSettings();
        console.log('从后端加载的配置:', backendConfig);
        if (backendConfig) {
          setConfig(backendConfig);
        }
      } catch (error) {
        console.error('从后端加载配置失败:', error);
      }
    };
    loadBackendConfig();

    return () => {
      unsubscribe();
    };
  }, []);

  return (
    <div className={`h-screen flex flex-col bg-background transition-colors duration-300 ${isDark ? 'dark' : ''}`}>
      {/* 自定义标题栏 */}
      <TitleBar />

      <div className="flex-1 flex overflow-hidden">
        {/* 侧边栏 */}
        <Sidebar />

        {/* 主内容区 */}
        <main className="flex-1 flex flex-col overflow-hidden bg-background dark:bg-background-dark">
          {/* 状态条 */}
          <div className="h-12 border-b border-border dark:border-border-dark flex items-center justify-between px-6 bg-white/50 dark:bg-background-dark/50 backdrop-blur-sm">
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 font-medium text-foreground-secondary dark:text-foreground-dark-secondary">
                <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-accent' : 'bg-danger'}`} />
                服务{isConnected ? '就绪' : '断开'}
              </span>
              {isProcessing && (
                <span className="flex items-center gap-1.5 text-primary font-semibold">
                  <Zap className="w-3 h-3 animate-pulse" />
                  处理中
                </span>
              )}
            </div>
          </div>

          {/* 滚动内容区 */}
          <div className="flex-1 overflow-y-auto p-8 space-y-12">
            <div className="max-w-4xl mx-auto space-y-10">
              {/* 上传区域 */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-foreground dark:text-foreground-dark">
                  <Layout className="w-5 h-5" />
                  <h2 className="text-xl font-bold tracking-tight">上传视频</h2>
                </div>
                <FileUploader maxFiles={10} />
              </section>

              {/* 文件列表与任务队列的组合 */}
              <div className="grid grid-cols-1 gap-10">
                <section className="space-y-4">
                  <h2 className="text-sm font-bold uppercase tracking-wider text-foreground-muted dark:text-foreground-dark-muted px-1">
                    待处理队列
                  </h2>
                  <FileGrid maxFiles={10} />
                </section>

                <section className="space-y-4">
                  <h2 className="text-sm font-bold uppercase tracking-wider text-foreground-muted dark:text-foreground-dark-muted px-1">
                    处理任务
                  </h2>
                  <TaskQueue />
                </section>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* 弹窗 */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setSettingsOpen(false)} 
      />
      <SubtitleEditorModal />
    </div>
  );
}

export default App;
