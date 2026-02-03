import React, { useState } from 'react';
import { useStore } from '../../store';
import { Task } from '../../types';
import { 
  PlayIcon, 
  PauseIcon, 
  TrashIcon, 
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface TaskActionsProps {
  task: Task;
}

export function TaskActions({ task }: TaskActionsProps) {
  const { updateTask, removeTask } = useStore();
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);

  const handleToggleStatus = () => {
    if (task.status === 'processing') {
      updateTask(task.id, { status: 'pending' });
    } else if (task.status === 'pending' || task.status === 'error') {
      updateTask(task.id, { status: 'processing' });
    }
  };

  const handleRemove = () => {
    if (isConfirmingDelete) {
      removeTask(task.id);
    } else {
      setIsConfirmingDelete(true);
      setTimeout(() => setIsConfirmingDelete(false), 3000);
    }
  };

  const getStatusIcon = () => {
    switch (task.status) {
      case 'processing':
        return <ArrowPathIcon className="w-4 h-4 animate-spin text-primary" />;
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4 text-green-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1.5 mr-2">
        {getStatusIcon()}
        <span className="text-xs text-foreground-muted capitalize">
          {task.status === 'processing' ? (task.stage || '处理中') : task.status}
        </span>
      </div>

      <div className="flex items-center bg-background dark:bg-background-dark border border-border dark:border-border-dark rounded-md p-0.5">
        <button
          onClick={handleToggleStatus}
          disabled={task.status === 'completed'}
          className={`
            p-1 rounded transition-colors
            ${task.status === 'processing' 
              ? 'text-yellow-500 hover:bg-yellow-500/10' 
              : 'text-primary hover:bg-primary/10'
            }
            disabled:opacity-30 disabled:hover:bg-transparent
          `}
          title={task.status === 'processing' ? '暂停' : '开始'}
        >
          {task.status === 'processing' ? (
            <PauseIcon className="w-4 h-4" />
          ) : (
            <PlayIcon className="w-4 h-4" />
          )}
        </button>

        <div className="w-px h-4 bg-border dark:bg-border-dark mx-0.5" />

        <button
          onClick={handleRemove}
          className={`
            p-1 rounded transition-colors
            ${isConfirmingDelete ? 'text-red-500 bg-red-500/10' : 'text-foreground-muted hover:text-red-500 hover:bg-red-500/10'}
          `}
          title={isConfirmingDelete ? '再次点击确认删除' : '删除任务'}
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
