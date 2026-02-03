"""音频处理模块 - 使用 FFmpeg 和 pydub 提取音频"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Callable
import subprocess

from pydub import AudioSegment

from utils.logger import get_logger
from utils.config import get_config

logger = get_logger("audio_processor")

# 尝试导入 ffmpeg-python，如果失败则使用备用方案
try:
    import ffmpeg

    FFMPEG_PYTHON_AVAILABLE = True
except ImportError:
    FFMPEG_PYTHON_AVAILABLE = False
    logger.warning("ffmpeg-python 不可用，将使用备用方案")


class AudioProcessor:
    """音频处理器"""

    def __init__(self):
        self.config = get_config()
        self.temp_dir = Path(self.config.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置 pydub 使用指定的 FFmpeg/FFprobe 路径
        if self.config.ffmpeg_path:
            AudioSegment.converter = self.config.ffmpeg_path
        if self.config.ffprobe_path:
            AudioSegment.ffprobe = self.config.ffprobe_path
            
        self.ffmpeg_path = self.config.ffmpeg_path or self._find_ffmpeg()
        logger.info(f"音频处理器初始化完成，临时目录: {self.temp_dir}")
        if self.ffmpeg_path:
            logger.info(f"FFmpeg 路径: {self.ffmpeg_path}")
        else:
            logger.warning("未找到 FFmpeg，音频提取功能将不可用")

    def _find_ffmpeg(self) -> Optional[str]:
        """查找 FFmpeg 可执行文件"""
        # 从当前文件位置向上查找项目根目录 (backend/core -> backend -> project_root)
        project_root = Path(__file__).parent.parent.parent
        ffmpeg_dir = project_root / "ffmpeg"

        # 1. 检查项目目录下的 ffmpeg 文件夹（直接放置）
        local_ffmpeg = ffmpeg_dir / "ffmpeg.exe"
        if local_ffmpeg.exists():
            return str(local_ffmpeg)

        # 2. 检查子目录结构（如 ffmpeg-master-latest-win64-gpl/bin/）
        for subdir in ffmpeg_dir.iterdir():
            if subdir.is_dir():
                nested_ffmpeg = subdir / "bin" / "ffmpeg.exe"
                if nested_ffmpeg.exists():
                    return str(nested_ffmpeg)

        # 3. 检查环境变量 PATH
        try:
            import subprocess

            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return "ffmpeg"
        except:
            pass

        return None

    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """
        从视频提取音频

        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径（可选）
            format: 音频格式，默认 wav
            sample_rate: 采样率，默认 16000（适合语音识别）
            channels: 声道数，默认 1（单声道）
            progress_callback: 进度回调函数

        Returns:
            音频文件路径
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 生成输出路径
        if output_path is None:
            output_path = self.temp_dir / f"{video_path.stem}_audio.{format}"
        else:
            output_path = Path(output_path)

        logger.info(f"开始提取音频: {video_path} -> {output_path}")

        # 检查 FFmpeg 是否可用
        if not self.ffmpeg_path:
            raise RuntimeError(
                "FFmpeg 未安装或未找到。请:\n"
                "1. 下载 FFmpeg 并解压到项目目录下的 ffmpeg/ 文件夹，或\n"
                "2. 将 FFmpeg 添加到系统环境变量 PATH\n"
                "下载地址: https://github.com/BtbN/FFmpeg-Builds/releases"
            )

        if progress_callback:
            progress_callback(0, "准备提取音频...")

        try:
            # 使用 subprocess 调用 FFmpeg（支持项目内或系统的 FFmpeg）
            cmd = [
                self.ffmpeg_path,
                "-i",
                str(video_path),
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                "-vn",  # 不保留视频
                "-y",  # 覆盖输出文件
                str(output_path),
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            if progress_callback:
                progress_callback(100, "音频提取完成")

            logger.info(f"音频提取完成: {output_path}")
            return str(output_path)

        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg 错误: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"提取音频失败: {e}")
            raise

    def get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频时长

        Args:
            audio_path: 音频文件路径

        Returns:
            时长（秒）
        """
        try:
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # 转换为秒
            logger.debug(f"音频时长: {duration:.2f}s - {audio_path}")
            return duration
        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            raise

    def _find_ffprobe(self) -> Optional[str]:
        """查找 ffprobe 可执行文件"""
        # 1. 优先使用配置路径
        if self.config.ffprobe_path and os.path.exists(self.config.ffprobe_path):
            return self.config.ffprobe_path

        # 2. 尝试与 ffmpeg 在同一目录
        if self.ffmpeg_path and self.ffmpeg_path != "ffmpeg":
            ffprobe_path = Path(self.ffmpeg_path).parent / "ffprobe.exe"
            if ffprobe_path.exists():
                return str(ffprobe_path)

        # 3. 尝试系统 PATH
        try:
            subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=2)
            return "ffprobe"
        except:
            pass

        return None

    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            时长（秒）
        """
        try:
            ffprobe_path = self._find_ffprobe()
            if not ffprobe_path:
                raise RuntimeError("未找到 ffprobe")

            # 使用 ffprobe 获取时长
            cmd = [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            logger.debug(f"视频时长: {duration:.2f}s - {video_path}")
            return duration
        except Exception as e:
            logger.error(f"获取视频时长失败: {e}")
            # 如果 ffprobe 失败，尝试使用 pydub 作为备用
            try:
                audio = AudioSegment.from_file(video_path)
                duration = len(audio) / 1000.0
                logger.debug(f"使用 pydub 获取视频时长: {duration:.2f}s - {video_path}")
                return duration
            except Exception as e2:
                logger.error(f"备用方案也失败: {e2}")
                raise

    def split_audio(
        self,
        audio_path: str,
        chunk_duration: float = 30.0,
        overlap: float = 1.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> list:
        """
        将音频分割成块（流式处理）

        Args:
            audio_path: 音频文件路径
            chunk_duration: 每块时长（秒）
            overlap: 重叠时长（秒）
            progress_callback: 进度回调函数

        Returns:
            音频块列表 [(start_time, end_time, audio_segment)]
        """
        logger.info(f"开始分割音频: {audio_path}, 块大小: {chunk_duration}s")

        try:
            audio = AudioSegment.from_file(audio_path)
            total_duration = len(audio) / 1000.0

            chunks = []
            chunk_ms = int(chunk_duration * 1000)
            overlap_ms = int(overlap * 1000)

            start = 0
            chunk_idx = 0

            while start < len(audio):
                end = min(start + chunk_ms, len(audio))
                chunk = audio[start:end]

                start_time = start / 1000.0
                end_time = end / 1000.0

                chunks.append((start_time, end_time, chunk))

                chunk_idx += 1
                if progress_callback and chunk_idx % 10 == 0:
                    progress = min(100, (end / len(audio)) * 100)
                    progress_callback(progress, f"分割音频块 {chunk_idx}...")

                # 移动到下一个位置（考虑重叠）
                start = end - overlap_ms if end < len(audio) else end

            logger.info(f"音频分割完成，共 {len(chunks)} 块")
            return chunks

        except Exception as e:
            logger.error(f"分割音频失败: {e}")
            raise

    def export_audio_segment(
        self,
        audio_segment: AudioSegment,
        output_path: str,
        format: str = "wav",
        sample_rate: int = 16000,
    ) -> str:
        """
        导出音频片段

        Args:
            audio_segment: 音频片段
            output_path: 输出路径
            format: 格式
            sample_rate: 采样率

        Returns:
            输出路径
        """
        try:
            audio_segment.export(
                output_path, format=format, parameters=["-ar", str(sample_rate)]
            )
            logger.debug(f"音频片段导出完成: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"导出音频片段失败: {e}")
            raise

    def extract_segment(
        self,
        audio_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None,
    ) -> str:
        """
        提取音频片段 (优化版：直接使用 FFmpeg 提取，避免加载整个文件到内存)

        Args:
            audio_path: 音频或视频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            output_path: 输出路径（可选）

        Returns:
            输出路径
        """
        audio_path_obj = Path(audio_path)
        if not audio_path_obj.exists():
            logger.error(f"提取片段失败：源文件不存在 -> {audio_path}")
            raise FileNotFoundError(f"源文件不存在: {audio_path}")

        if output_path is None:
            output_path = self.temp_dir / f"segment_{start_time:.3f}_{end_time:.3f}.wav"
        else:
            output_path = Path(output_path)

        logger.debug(f"正在提取音频片段: {audio_path} [{start_time}s - {end_time}s]")

        try:
            # 使用 FFmpeg 直接提取片段，这样更快且不占用内存
            duration = end_time - start_time
            cmd = [
                self.ffmpeg_path,
                "-ss", str(start_time),
                "-t", str(duration),
                "-i", str(audio_path),
                "-vn",  # 只要音频
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y",
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return str(output_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 提取片段失败: {e.stderr}")
            # 备用方案：使用 pydub (如果 FFmpeg 失败)
            try:
                logger.info("尝试使用 pydub 作为备用提取方案...")
                audio = AudioSegment.from_file(audio_path)
                start_ms = int(start_time * 1000)
                end_ms = int(end_time * 1000)
                segment = audio[start_ms:end_ms]
                segment.export(output_path, format="wav")
                return str(output_path)
            except Exception as e2:
                logger.error(f"备用提取方案也失败: {e2}")
                raise e2
        except Exception as e:
            logger.error(f"提取音频片段失败: {e}")
            raise

    def adjust_audio_speed(
        self,
        input_path: str,
        output_path: str,
        speed_factor: float,
        pitch_shift: bool = False,
    ) -> str:
        """
        调整音频语速 (Time Stretching)

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            speed_factor: 语速倍率 (1.0 为原始速度, >1.0 加快, <1.0 减慢)
            pitch_shift: 是否改变音调 (默认不改变，使用 atempo 滤镜)

        Returns:
            输出路径
        """
        if abs(speed_factor - 1.0) < 0.01:
            # 速度几乎没变，直接复制或导出
            if input_path != output_path:
                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format="mp3")
            return output_path

        logger.debug(f"正在调整音频速度: {speed_factor:.2f}x -> {input_path}")

        try:
            # 构造 atempo 滤镜链
            # ffmpeg 的 atempo 滤镜限制在 0.5 到 2.0 之间，超出范围需要串联
            filters = []
            temp_factor = speed_factor
            
            while temp_factor > 2.0:
                filters.append("atempo=2.0")
                temp_factor /= 2.0
            while temp_factor < 0.5:
                filters.append("atempo=0.5")
                temp_factor /= 0.5
            filters.append(f"atempo={temp_factor}")
            
            filter_str = ",".join(filters)

            cmd = [
                self.ffmpeg_path,
                "-i", str(input_path),
                "-filter:a", filter_str,
                "-y",
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return str(output_path)

        except Exception as e:
            logger.error(f"调整音频速度失败: {e}")
            # 备用方案：使用 pydub (会改变音调)
            try:
                audio = AudioSegment.from_file(input_path)
                # pydub 改变速度的方法会改变采样率，从而改变音调
                new_sample_rate = int(audio.frame_rate * speed_factor)
                alt_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
                alt_audio = alt_audio.set_frame_rate(audio.frame_rate)
                alt_audio.export(output_path, format="mp3")
                return str(output_path)
            except Exception as e2:
                logger.error(f"备用速度调整方案也失败: {e2}")
                raise e2

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            count = 0
            for file_path in self.temp_dir.glob("*.wav"):
                if file_path.is_file():
                    file_path.unlink()
                    count += 1
            logger.info(f"清理了 {count} 个临时音频文件")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
