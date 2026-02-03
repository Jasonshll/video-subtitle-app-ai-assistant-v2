import React from 'react';
import { useStore } from '../../store';
import { TaskActions } from './TaskActions';

export function TaskQueue() {
  const { tasks } = useStore();
  const activeTasks = tasks.filter(t => t.status !== 'completed');

  if (activeTasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-foreground-muted">
        <p className="text-sm">暂无进行中的任务</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-border dark:border-border-dark">
        <h3 className="text-sm font-semibold">任务队列 ({activeTasks.length})</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {activeTasks.map((task) => (
          <div 
            key={task.id}
            className="p-3 bg-background dark:bg-background-dark border border-border dark:border-border-dark rounded-lg space-y-2"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate" title={task.name}>
                  {task.name}
                </p>
                <p className="text-xs text-foreground-muted truncate">
                  {task.path}
                </p>
              </div>
              <TaskActions task={task} />
            </div>

            {task.status === 'processing' && (
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-foreground-muted">
                  <span>{task.stageDetail || '准备中...'}</span>
                  <span>{Math.round(task.progress || 0)}%</span>
                </div>
                <div className="w-full h-1 bg-border dark:bg-border-dark rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${task.progress || 0}%` }}
                  />
                </div>
              </div>
            )}

            {task.status === 'error' && task.error && (
              <p className="text-xs text-red-500 bg-red-500/5 p-2 rounded border border-red-500/20">
                错误: {task.error}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
