import axios, { AxiosInstance, AxiosError } from 'axios';
import type { 
  ApiResponse, 
  AppConfig,
  VideoTask, 
  SubtitleEntry, 
  ExportOptions,
  FileInfo 
} from '../types';
import { useStore } from '../store';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000, // 增加全局超时到 60 秒
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        const { config: appConfig } = useStore.getState();
        if (appConfig.apiKey) {
          config.headers['X-API-Key'] = appConfig.apiKey;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => response.data,
      (error: AxiosError<ApiResponse>) => {
        console.error('API Error:', error);
        if (error.code === 'ECONNABORTED') {
          return Promise.reject('请求超时，请检查网络或稍后重试');
        }
        return Promise.reject(error.response?.data?.error || '网络请求失败');
      }
    );
  }

  // 健康检查
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/api/health') as ApiResponse;
      return response.success;
    } catch {
      return false;
    }
  }

  // 创建任务
  async createTask(filePath: string, fileName: string, fileSize: number): Promise<VideoTask> {
    const response = await this.client.post('/api/tasks', {
      file_path: filePath,
      file_name: fileName,
      file_size: fileSize,
    }) as ApiResponse<VideoTask>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '创建任务失败');
    }
    
    return response.data;
  }

  // 批量创建任务
  async createTasks(files: FileInfo[]): Promise<VideoTask[]> {
    const response = await this.client.post('/api/tasks/batch', {
      files: files.map(f => ({
        file_path: f.filePath,
        file_name: f.fileName,
        file_size: f.fileSize,
      })),
    }) as ApiResponse<VideoTask[]>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '批量创建任务失败');
    }
    
    return response.data;
  }

  // 获取任务列表
  async getTasks(): Promise<VideoTask[]> {
    const response = await this.client.get('/api/tasks') as ApiResponse<VideoTask[]>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '获取任务列表失败');
    }
    
    return response.data;
  }

  // 获取单个任务
  async getTask(id: string): Promise<VideoTask> {
    const response = await this.client.get(`/api/tasks/${id}`) as ApiResponse<VideoTask>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '获取任务失败');
    }
    
    return response.data;
  }

  // 开始处理视频（创建并启动任务）
  async startTask(filePath: string, fileName?: string, fileSize?: number, taskId?: string): Promise<VideoTask> {
    const response = await this.client.post('/api/process', {
      filePath,
      fileName,
      fileSize,
      taskId,
    }) as ApiResponse<VideoTask>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '启动任务失败');
    }
    
    return response.data;
  }

  // 暂停任务
  async pauseTask(id: string): Promise<void> {
    const response = await this.client.post(`/api/tasks/${id}/pause`) as ApiResponse;
    
    if (!response.success) {
      throw new Error(response.error || '暂停任务失败');
    }
  }

  // 恢复任务
  async resumeTask(id: string): Promise<void> {
    const response = await this.client.post(`/api/tasks/${id}/resume`) as ApiResponse;
    
    if (!response.success) {
      throw new Error(response.error || '恢复任务失败');
    }
  }

  // 取消任务
  async cancelTask(id: string): Promise<void> {
    const response = await this.client.post(`/api/tasks/${id}/cancel`) as ApiResponse;
    
    if (!response.success) {
      throw new Error(response.error || '取消任务失败');
    }
  }

  // 删除任务
  async deleteTask(id: string): Promise<void> {
    const response = await this.client.delete(`/api/tasks/${id}`) as ApiResponse;
    
    if (!response.success) {
      throw new Error(response.error || '删除任务失败');
    }
  }

  // 更新字幕
  async updateSubtitles(id: string, subtitles: SubtitleEntry[]): Promise<void> {
    const response = await this.client.put(`/api/tasks/${id}/subtitles`, {
      subtitles,
    }) as ApiResponse;
    
    if (!response.success) {
      throw new Error(response.error || '更新字幕失败');
    }
  }

  // 导出字幕
  async exportSubtitles(
    id: string, 
    options: ExportOptions,
    savePath: string
  ): Promise<string> {
    const response = await this.client.post('/api/export', {
      taskId: id,
      format: options.format,
      outputPath: savePath,
      includeTimestamp: options.includeTimestamp,
    }) as ApiResponse<{ filePath: string }>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '导出字幕失败');
    }
    
    return response.data.filePath;
  }

  // 获取导出内容（用于下载）
  async getExportContent(id: string, options: ExportOptions): Promise<string> {
    const response = await this.client.post('/api/tasks/export/content', {
      taskId: id,
      format: options.format,
      encoding: options.encoding,
      includeTimestamp: options.includeTimestamp,
    }) as ApiResponse<{ content: string }>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '获取导出内容失败');
    }
    
    return response.data.content;
  }

  // 上传文件（用于 Web 环境）
  async uploadFile(file: File, onProgress?: (progress: number) => void): Promise<FileInfo> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post(
      '/api/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      }
    ) as ApiResponse<FileInfo>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '上传文件失败');
    }
    
    return response.data;
  }

  // 批量上传文件
  async uploadFiles(
    files: File[], 
    onProgress?: (index: number, progress: number) => void
  ): Promise<FileInfo[]> {
    const uploadedFiles: FileInfo[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const fileInfo = await this.uploadFile(files[i], (progress) => {
        onProgress?.(i, progress);
      });
      uploadedFiles.push(fileInfo);
    }
    
    return uploadedFiles;
  }

  // 获取配置
  async getSettings(): Promise<AppConfig | null> {
    try {
      const response = await this.client.get('/api/settings') as ApiResponse<AppConfig>;
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error('获取配置失败:', error);
      return null;
    }
  }

  // 保存配置
  async saveSettings(config: Partial<AppConfig>): Promise<void> {
    const response = await this.client.post('/api/settings', config) as ApiResponse;
    
    if (!response.success) {
      throw new Error(response.error || '保存配置失败');
    }
  }

  // 更新配置项
  async updateConfig(key: string, value: any): Promise<void> {
    await this.saveSettings({ [key]: value });
  }

  // 验证 API Key
  async validateApiKey(apiKey: string): Promise<boolean> {
    // 先保存 API Key 到配置
    await this.updateConfig('apiKey', apiKey);
    
    const response = await this.client.post('/api/check-api-key', {
      apiKey,
    }) as ApiResponse<{ valid: boolean }>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '验证失败');
    }
    
    return response.data.valid;
  }

  // 翻译字幕（支持分批并行）
  async translateSubtitles(
    subtitles: SubtitleEntry[], 
    targetLang: string, 
    model?: string,
    batchSize?: number,
    maxWorkers?: number,
    taskId?: string
  ): Promise<SubtitleEntry[]> {
    const response = await this.client.post('/api/translate', {
      subtitles,
      targetLang,
      model,
      batchSize,
      maxWorkers,
      taskId,
    }, {
      timeout: 600000, // 翻译请求可能很慢，设置 10 分钟超时
    }) as ApiResponse<SubtitleEntry[]>;

    if (!response.success || !response.data) {
      throw new Error(response.error || '翻译失败');
    }

    return response.data;
  }

  // 获取字幕预览图
  async getSubtitlePreview(
    text: string, 
    style: any, 
    taskId?: string,
    bilingual?: boolean,
    videoPath?: string
  ): Promise<string> {
    const response = await this.client.post('/api/subtitle/preview', {
      text,
      style,
      taskId,      // 任务ID（用于获取视频背景）
      bilingual,   // 是否双语预览
      videoPath,
    }) as ApiResponse<{ url: string }>;
    
    if (!response.success || !response.data) {
      throw new Error(response.error || '生成预览失败');
    }

    // 如果返回的是相对路径，补全为绝对路径
    const url = response.data.url;
    if (url.startsWith('/')) {
      return `${API_BASE_URL}${url}`;
    }
    return url;
  }

  // 压制视频
  async synthesizeVideo(
    taskId: string, 
    style: any,
    bilingual?: boolean,
    videoPath?: string
  ): Promise<void> {
    const response = await this.client.post(`/api/tasks/${taskId}/synthesize`, {
      style,
      bilingual,  // 是否启用双语字幕
      videoPath,
    }) as ApiResponse<{ status: string }>;

    if (!response.success) {
      throw new Error(response.error || '压制失败');
    }
  }

  // 原声配音
  async dubVideo(
    taskId: string, 
    style: any,
    bilingual?: boolean,
    videoPath?: string,
  ): Promise<void> {
    const response = await this.client.post(`/api/tasks/${taskId}/dub`, {
      style,
      bilingual,
      video_path: videoPath,
    }) as ApiResponse<{ status: string }>;

    if (!response.success) {
      throw new Error(response.error || '启动配音失败');
    }
  }

}

export const apiService = new ApiService();
export default apiService;
