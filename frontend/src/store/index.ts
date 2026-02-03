import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AppConfig, VideoTask, TaskStatus } from '../types';

// Re-export wsService for convenience
export { wsService } from '../services/websocket';

interface AppState {
  // 配置
  config: AppConfig;
  setConfig: (config: Partial<AppConfig>) => void;
  updateConfig: (key: keyof AppConfig, value: any) => void;
  resetConfig: () => void;
  
  // 主题
  isDark: boolean;
  toggleTheme: () => void;
  setTheme: (isDark: boolean) => void;
  
  // 任务队列
  tasks: VideoTask[];
  addTask: (task: VideoTask) => void;
  updateTask: (id: string, updates: Partial<VideoTask>) => void;
  removeTask: (id: string) => void;
  clearCompleted: () => void;
  clearAll: () => void;
  
  // 选中任务
  selectedTaskId: string | null;
  setSelectedTask: (id: string | null) => void;
  
  // 模态框状态
  isSettingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
  
  isEditorOpen: boolean;
  setEditorOpen: (open: boolean) => void;
  
  // 处理状态
  isProcessing: boolean;
  setProcessing: (processing: boolean) => void;
  
  // 计算属性
  getTaskById: (id: string) => VideoTask | undefined;
  getPendingTasks: () => VideoTask[];
  getCompletedTasks: () => VideoTask[];
  getActiveTasks: () => VideoTask[];
  getTaskCount: () => number;
}

export const defaultConfig: AppConfig = {
  apiKey: '',
  theme: 'dark',
  vadSensitivity: 0.4,
  minSilenceDuration: 0.05,
  mergeThreshold: 0.5,
  defaultExportFormat: 'srt',
  maxConcurrentTasks: 3,
  asrLanguage: 'zh',
  apiModel: 'iic/SenseVoiceSmall',
  maxSubtitleLength: 30,
  enableMaxSubtitleLength: true,
  maxSpeechDuration: 30,
  languageGuard: false,
  autoRemoveDrift: false,
  contextRetry: false,
  translationModel: '',
  translationTargetLang: 'en',
  customTranslationModels: [],
  translationBatchSize: 20,
  translationMaxWorkers: 3,
  ttsMaxWorkers: 2,
  // 导出路径配置
  exportPath: '',
  exportSubtitlePath: '',
  useSourceFolder: true,
  videoFilenamePrefix: '【阿泽】',
  subtitleStyle: {
    // 基础样式（新默认值）
    fontname: 'Arial',
    fontsize: 75,              // 默认75（更大更清楚）
    primary_color: '#FFA500',  // 橙黄色
    outline_color: '#000000',  // 黑色描边
    back_color: '#000000',     // 黑色背景
    outline_width: 2.0,        // 加粗描边
    shadow_width: 0,
    alignment: 2,
    margin_v: 30,
    bold: true,                // 默认加粗
    italic: false,
    border_style: 3,           // 背景框模式
    alpha: 0,
    
    // 背景效果
    background_alpha: 128,     // 50%透明背景
    
    // 双语字幕（默认关闭）
    bilingual: false,
    translation_on_top: true,      // 译文在上（默认）
    translation_fontsize: 75,      // 译文字号（大）
    original_fontsize: 45,         // 原文字号（小）
    translation_color: '#FFA500',  // 译文橙黄
    original_color: '#FFFFFF',     // 原文白色
    translation_outline_color: '#000000',
    original_outline_color: '#000000',
    line_spacing: 30,              // 行间距（默认30，可调）
    translation_margin_v: 80,      // 译文边距（默认80，从底部向上定位）
    original_margin_v: 30,         // 原文边距（默认30，用户可调）
  },
};

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 配置
      config: defaultConfig,
      setConfig: (config) =>
        set((state) => ({
          config: { ...state.config, ...config },
        })),
      updateConfig: (key, value) =>
        set((state) => ({
          config: { ...state.config, [key]: value },
        })),
      resetConfig: () =>
        set((state) => ({
          config: { ...defaultConfig, apiKey: state.config.apiKey },
        })),

      // 主题
      isDark: true,
      toggleTheme: () =>
        set((state) => {
          const newIsDark = !state.isDark;
          if (newIsDark) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
          return { isDark: newIsDark };
        }),
      setTheme: (isDark) => {
        if (isDark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        set({ isDark });
      },

      // 任务队列
      tasks: [],
      addTask: (task) =>
        set((state) => ({
          tasks: [...state.tasks, task],
        })),
      updateTask: (id, updates) =>
        set((state) => ({
          tasks: state.tasks.map((task) =>
            task.id === id ? { ...task, ...updates, updatedAt: Date.now() } : task
          ),
        })),
      removeTask: (id) =>
        set((state) => ({
          tasks: state.tasks.filter((task) => task.id !== id),
          selectedTaskId: state.selectedTaskId === id ? null : state.selectedTaskId,
        })),
      clearCompleted: () =>
        set((state) => ({
          tasks: state.tasks.filter(
            (task) => !['completed', 'failed', 'cancelled'].includes(task.status)
          ),
        })),
      clearAll: () =>
        set({
          tasks: [],
          selectedTaskId: null,
        }),

      // 选中任务
      selectedTaskId: null,
      setSelectedTask: (id) => set({ selectedTaskId: id }),

      // 模态框状态
      isSettingsOpen: false,
      setSettingsOpen: (open) => set({ isSettingsOpen: open }),

      isEditorOpen: false,
      setEditorOpen: (open) => set({ isEditorOpen: open }),

      // 处理状态
      isProcessing: false,
      setProcessing: (processing) => set({ isProcessing: processing }),

      // 计算属性
      getTaskById: (id) => get().tasks.find((task) => task.id === id),
      getPendingTasks: () =>
        get().tasks.filter((task) => task.status === 'pending'),
      getCompletedTasks: () =>
        get().tasks.filter((task) => task.status === 'completed'),
      getActiveTasks: () =>
        get().tasks.filter(
          (task) => task.status === 'processing' || task.status === 'pending'
        ),
      getTaskCount: () => get().tasks.length,
    }),
    {
      name: 'video-subtitle-app-storage',
      partialize: (state) => ({
        config: state.config,
        isDark: state.isDark,
      }),
      // 自定义合并逻辑，确保新增加的配置项能正确合并
      merge: (persistedState: any, currentState) => {
        const mergedConfig = {
          ...currentState.config,
          ...(persistedState?.config || {}),
          // 深度合并 subtitleStyle
          subtitleStyle: {
            ...currentState.config.subtitleStyle,
            ...(persistedState?.config?.subtitleStyle || {}),
          }
        };
        return {
          ...currentState,
          ...persistedState,
          config: mergedConfig
        };
      },
      onRehydrateStorage: () => (state) => {
        if (state) {
          if (state.isDark) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        }
      },
    }
  )
);

// 辅助函数：生成唯一ID
export const generateTaskId = () => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// 辅助函数：格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 辅助函数：格式化时长
export const formatDuration = (seconds: number): string => {
  if (!seconds) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// 辅助函数：获取状态颜色
export const getStatusColor = (status: TaskStatus): string => {
  const colors: Record<TaskStatus, string> = {
    pending: 'text-foreground-muted',
    processing: 'text-primary-light',
    paused: 'text-warning',
    completed: 'text-accent',
    failed: 'text-danger',
    cancelled: 'text-foreground-muted',
  };
  return colors[status] || 'text-foreground';
};

// 辅助函数：获取状态标签
export const getStatusLabel = (status: TaskStatus): string => {
  const labels: Record<TaskStatus, string> = {
    pending: '等待中',
    processing: '处理中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  };
  return labels[status] || status;
};
