import { io, Socket } from 'socket.io-client';
import type { ProgressUpdate, VideoTask } from '../types';
import { useStore } from '../store';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:5000';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  // 连接 WebSocket
  connect(): void {
    if (this.socket?.connected) return;

    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      timeout: 20000,
    });

    this.setupEventHandlers();
  }

  // 断开连接
  disconnect(): void {
    this.socket?.disconnect();
    this.socket = null;
  }

  // 检查连接状态
  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  // 设置事件处理器
  private setupEventHandlers(): void {
    if (!this.socket) return;

    // 连接成功
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connection', { status: 'connected' });
    });

    // 连接断开
    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('connection', { status: 'disconnected', reason });
    });

    // 连接错误
    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.emit('connection', { 
        status: 'error', 
        error: error.message,
        attempts: this.reconnectAttempts 
      });
    });

    // 任务进度更新
    this.socket.on('task_progress', (update: ProgressUpdate) => {
      this.handleProgressUpdate(update);
      this.emit('progress', update);
    });

    // 翻译进度更新
    this.socket.on('translation_progress', (data: any) => {
      console.log('Translation progress:', data);
      this.emit('translation_progress', data);
    });

    // 翻译完成
    this.socket.on('translation_completed', (data: any) => {
      console.log('Translation completed:', data);
      this.emit('translation_completed', data);
    });

    // 实时字幕增加
    this.socket.on('subtitle_added', (data: { taskId: string; subtitle: any }) => {
      this.handleSubtitleAdded(data);
      this.emit('subtitle_added', data);
    });

    // 任务完成
    this.socket.on('task_completed', (task: VideoTask) => {
      const { updateTask } = useStore.getState();
      updateTask(task.id, {
        status: 'completed',
        progress: 100,
        stage: 'completed',
        stageDetail: '处理完成',
        subtitles: task.subtitles,
        completedAt: Date.now(),
      });
      this.emit('completed', task);
    });

    // 任务失败
    this.socket.on('task_failed', ({ taskId, error }: { taskId: string; error: string }) => {
      const { updateTask } = useStore.getState();
      updateTask(taskId, {
        status: 'failed',
        error,
        stageDetail: `处理失败: ${error}`,
      });
      this.emit('failed', { taskId, error });
    });

    // 视频压制进度
    this.socket.on('synthesis_progress', (data: { taskId: string; progress: number; detail: string; timestamp: number }) => {
      console.log('Synthesis progress:', data);
      const { updateTask } = useStore.getState();
      updateTask(data.taskId, {
        progress: data.progress,
        stage: 'generating_subtitle',
        stageDetail: data.detail,
      });
      this.emit('synthesis_progress', data);
    });

    // 视频压制完成
    this.socket.on('synthesis_completed', (data: { taskId: string; outputPath: string; timestamp: number }) => {
      console.log('Synthesis completed:', data);
      const { updateTask } = useStore.getState();
      updateTask(data.taskId, {
        status: 'completed',
        progress: 100,
        stage: 'completed',
        stageDetail: '视频合成完成',
      });
      this.emit('synthesis_completed', data);
    });

    // 视频压制失败
    this.socket.on('synthesis_failed', (data: { taskId: string; error: string; timestamp: number }) => {
      console.error('Synthesis failed:', data);
      const { updateTask } = useStore.getState();
      updateTask(data.taskId, {
        status: 'failed',
        error: data.error,
        stageDetail: `合成失败: ${data.error}`,
      });
      this.emit('synthesis_failed', data);
    });

    // 任务取消
    this.socket.on('task_cancelled', (taskId: string) => {
      const { updateTask } = useStore.getState();
      updateTask(taskId, {
        status: 'cancelled',
        stageDetail: '已取消',
      });
      this.emit('cancelled', taskId);
    });

    // 所有任务完成
    this.socket.on('all_tasks_completed', () => {
      const { setProcessing } = useStore.getState();
      setProcessing(false);
      this.emit('allCompleted', null);
    });
  }

  // 处理进度更新
  private handleProgressUpdate(update: ProgressUpdate): void {
    const { updateTask } = useStore.getState();
    updateTask(update.taskId, {
      progress: update.progress,
      stage: update.stage,
      stageDetail: update.detail,
    });
  }

  // 处理实时字幕
  private handleSubtitleAdded(data: { taskId: string; subtitle: any }): void {
    const { updateTask, getTaskById } = useStore.getState();
    const task = getTaskById(data.taskId);
    if (task) {
      const currentSubtitles = task.subtitles || [];
      const raw = data.subtitle || {};
      const normalized = {
        id: raw.id,
        startTime: typeof raw.startTime === 'number' ? raw.startTime : raw.start,
        endTime: typeof raw.endTime === 'number' ? raw.endTime : raw.end,
        text: raw.text ?? '',
        confidence: raw.confidence,
      };
      if (typeof normalized.startTime !== 'number' || typeof normalized.endTime !== 'number') return;
      // 避免重复添加（虽然并行的 ID 可能不按顺序，但 ID 应该是唯一的）
      if (!currentSubtitles.find(s => s.id === normalized.id)) {
        const newSubtitles = [...currentSubtitles, normalized].sort((a, b) => a.startTime - b.startTime);
        updateTask(data.taskId, { subtitles: newSubtitles });
      }
    }
  }

  // 订阅事件
  on(event: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    // 返回取消订阅函数
    return () => {
      this.listeners.get(event)?.delete(callback);
    };
  }

  // 取消订阅
  off(event: string, callback: (data: any) => void): void {
    this.listeners.get(event)?.delete(callback);
  }

  // 触发事件
  private emit(event: string, data: any): void {
    this.listeners.get(event)?.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${event} listener:`, error);
      }
    });
  }

  // 发送消息
  emitEvent(event: string, data?: any): void {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected');
      return;
    }
    this.socket.emit(event, data);
  }

  // 开始处理队列
  startQueue(taskIds: string[]): void {
    this.emitEvent('start_queue', { task_ids: taskIds });
  }

  // 暂停队列
  pauseQueue(): void {
    this.emitEvent('pause_queue');
  }

  // 恢复队列
  resumeQueue(): void {
    this.emitEvent('resume_queue');
  }

  // 取消队列
  cancelQueue(): void {
    this.emitEvent('cancel_queue');
  }

  // 取消指定任务
  cancelTask(taskId: string): void {
    this.emitEvent('cancel_task', { task_id: taskId });
  }
}

export const wsService = new WebSocketService();
export default wsService;

// React Hook 用于监听 WebSocket 事件
export function useWebSocket(event: string, callback: (data: any) => void) {
  wsService.on(event, callback);
  
  return () => {
    wsService.off(event, callback);
  };
}
