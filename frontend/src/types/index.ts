// 应用配置
export interface AppConfig {
  apiKey: string;
  theme: 'light' | 'dark';
  vadSensitivity: number;  // 0.1 - 0.9
  minSilenceDuration: number; // 秒，最小静音时长
  mergeThreshold: number;  // 秒，合并短段落阈值
  defaultExportFormat: 'srt' | 'txt';
  maxConcurrentTasks: number;  // 最大并发数，默认3
  asrLanguage: 'zh' | 'en' | 'ja' | 'ko';
  apiModel: 'iic/SenseVoiceSmall' | 'TeleAI/TeleSpeechASR';
  maxSubtitleLength: number;
  enableMaxSubtitleLength: boolean;
  maxSpeechDuration: number;
  languageGuard: boolean;
  autoRemoveDrift: boolean;
  contextRetry: boolean;
  translationModel: string;
  translationTargetLang: string;
  customTranslationModels: string[];
  translationBatchSize: number;  // 单次翻译条数，默认20
  translationMaxWorkers: number;  // 翻译并发数，默认3
  ttsMaxWorkers: number;  // 配音并发数，默认2
  subtitleStyle: SubtitleStyle;
  // 导出路径配置
  exportPath: string;  // 视频导出路径
  exportSubtitlePath: string;  // 字幕导出路径
  useSourceFolder: boolean;  // 是否使用原文件所在文件夹
  videoFilenamePrefix: string;  // 视频文件名前缀，默认【阿泽】
}

export interface SubtitleStyle {
  // 基础样式
  fontname: string;
  fontsize: number;
  primary_color: string;
  outline_color: string;
  back_color: string;
  outline_width: number;
  shadow_width: number;
  alignment: number;
  margin_v: number;
  bold: boolean;
  italic: boolean;
  border_style: number;
  alpha: number;
  
  // 背景相关
  background_alpha: number;      // 背景透明度 0-255
  
  // 双语字幕配置
  bilingual: boolean;            // 是否启用双语字幕
  translation_on_top: boolean;   // 译文在上（true）还是原文在上（false）
  translation_fontsize: number;  // 译文字号
  original_fontsize: number;     // 原文字号
  translation_color: string;     // 译文颜色
  original_color: string;        // 原文颜色
  translation_outline_color: string;  // 译文描边颜色
  original_outline_color: string;     // 原文描边颜色
  line_spacing: number;          // 原文与译文间距
  translation_margin_v: number;  // 译文底部边距
  original_margin_v: number;     // 原文底部边距
}

// 视频任务状态
export type TaskStatus = 'pending' | 'processing' | 'paused' | 'completed' | 'failed' | 'cancelled';

// 视频任务
export interface VideoTask {
  id: string;
  filePath: string;
  fileName: string;
  fileSize: number;  // 字节
  duration?: number;  // 视频时长（秒）
  status: TaskStatus;
  progress: number;  // 0-100
  stage: TaskStage;
  stageDetail: string;  // 详细状态描述
  error?: string;
  subtitles?: SubtitleEntry[];
  createdAt: number;
  updatedAt: number;
  completedAt?: number;
}

// 处理阶段
export type TaskStage = 
  | 'idle'
  | 'extracting_audio' 
  | 'vad_detecting' 
  | 'transcribing' 
  | 'generating_subtitle'
  | 'completed'
  | 'failed';

// 字幕条目
export interface SubtitleEntry {
  id: number;
  startTime: number;  // 秒，精确到小数点后3位
  endTime: number;
  text: string;
  translation?: string;
  confidence?: number;  // 置信度 0-1
  originalText?: string;
  detectedLang?: string;
  langMismatch?: boolean;
}

// WebSocket 进度更新
export interface ProgressUpdate {
  taskId: string;
  stage: TaskStage;
  progress: number;
  detail: string;
  timestamp: number;
  currentSegment?: number;
  totalSegments?: number;
}

// 后端响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 导出选项
export interface ExportOptions {
  format: 'srt' | 'txt';
  encoding: 'utf-8' | 'gbk';
  includeTimestamp: boolean;  // 纯文本时是否包含时间戳
}

// 文件信息
export interface FileInfo {
  filePath: string;
  fileName: string;
  fileSize: number;
}

// Electron API（preload 暴露）
export interface ElectronAPI {
  selectFiles: () => Promise<string[]>;
  selectSavePath: (defaultName: string) => Promise<string | undefined>;
  getAppPath: () => Promise<string>;
  openDirectory: (dirPath: string) => Promise<boolean>;
  platform: string;
  saveConfig: (config: AppConfig) => void;
  loadConfig: () => AppConfig | null;
  minimize: () => void;
  maximize: () => void;
  close: () => void;
}

// 全局 window 扩展
declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}
