import { SubtitleEntry } from '../types'

// 格式化时间 (秒 -> 00:00:00,000)
export function formatSrtTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)

  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`
}

// 导出模式
export type ExportMode = 'original' | 'translated' | 'bilingual' | 'bilingual_tagged'

// 生成 SRT 内容
export function generateSrtContent(subtitles: SubtitleEntry[], mode: ExportMode = 'original'): string {
  return subtitles.map((sub, index) => {
    const startTime = formatSrtTime(sub.startTime);
    const endTime = formatSrtTime(sub.endTime);

    let content = '';
    if (mode === 'original') {
      content = sub.originalText || sub.text;
    } else if (mode === 'translated') {
      content = sub.text;
    } else if (mode === 'bilingual') {
      const original = sub.originalText || sub.text;
      const translation = sub.text;
      // 如果没有翻译或翻译与原文一致，只显示一行
      if (original === translation && !sub.originalText) {
        content = original;
      } else {
        content = `${original}\n${translation}`;
      }
    } else if (mode === 'bilingual_tagged') {
      const original = sub.originalText || sub.text;
      const translation = sub.text;
      if (original === translation && !sub.originalText) {
        content = `[O]${original}`;
      } else {
        content = `[O]${original}\n[T]${translation}`;
      }
    }

    return `${index + 1}\n${startTime} --> ${endTime}\n${content}\n`
  }).join('\n')
}

// 格式化文件大小
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 防抖函数
export function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}
