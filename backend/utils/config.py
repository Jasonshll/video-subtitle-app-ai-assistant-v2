"""配置管理模块"""

import json
import os
import time
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

from .logger import get_logger

logger = get_logger("config")


@dataclass
class Config:
    """应用配置类"""

    # API 配置
    api_key: str = ""
    api_base_url: str = "https://api.siliconflow.cn/v1"
    api_model: str = "iic/SenseVoiceSmall"

    # VAD 配置
    vad_sensitivity: float = 0.4  # 0.1 - 0.9
    vad_threshold: float = 0.5
    min_speech_duration: float = 0.1  # 最小语音段落时长（秒），降低以避免漏掉短句
    min_silence_duration: float = 0.05  # 最小静音时长（秒），用于切分段落
    max_speech_duration: float = 5.0  # 最大语音段落时长（秒），确保字幕时间戳不超过5秒

    # 字幕合并配置
    merge_threshold: float = 0.5  # 秒，合并短段落阈值
    max_subtitle_length: int = 30  # 最大字幕长度（字符）
    enable_max_subtitle_length: bool = True  # 是否开启最大字数限制

    # 任务配置
    max_concurrent_tasks: int = 3
    chunk_duration: float = 30.0  # 音频分块时长（秒）
    asr_language: str = "zh"
    language_guard: bool = False
    auto_remove_drift: bool = False  # 是否自动删除疑似偏差字幕
    context_retry: bool = False
    context_retry_padding: float = 0.25

    # VAD配置
    vad_min_volume_db: float = -40.0  # VAD最小音量阈值 (dB)
    vad_enable_volume_filter: bool = True  # 是否启用音量过滤

    # 翻译配置
    translation_model: str = ""  # 默认空，必须用户手动设置
    translation_target_lang: str = "en"
    custom_translation_models: list = field(
        default_factory=list  # 默认空列表
    )
    translation_batch_size: int = 20  # 单次翻译条数
    translation_max_workers: int = 3  # 翻译并发数

    # TTS 配置
    tts_model: str = "IndexTeam/IndexTTS-2"
    tts_voice_name: str = "cloned_voice"
    tts_batch_size: int = 5
    tts_max_workers: int = 2

    # FFmpeg 配置
    ffmpeg_path: str = ""
    ffprobe_path: str = ""

    # 字幕样式配置 (用于 FFmpeg 压制)
    subtitle_style: dict = field(
        default_factory=lambda: {
            "fontname": "Arial",
            "fontsize": 70,  # 默认字号70（适合1080p视频）
            "primary_color": "#FFA500",  # 橙黄色（HEX格式，便于前端使用）
            "outline_color": "#000000",  # 黑色描边
            "back_color": "#000000",  # 黑色背景
            "outline_width": 2.0,  # 加粗描边
            "shadow_width": 0,
            "alignment": 2,  # 2 = 底部居中
            "margin_v": 30,
            "bold": True,  # 默认加粗
            "italic": False,
            "border_style": 3,  # 3 = 不透明背景框（实现背景效果）
            "alpha": 0,  # 0 为不透明, 255 为完全透明
            # 背景相关
            "background_alpha": 128,  # 背景透明度（128=50%透明）
            # 双语字幕配置
            "bilingual": False,  # 是否启用双语字幕
            "translation_on_top": True,  # 译文在上（默认）
            "translation_fontsize": 70,  # 译文字号（默认大）
            "original_fontsize": 45,  # 原文字号（默认小）
            "translation_color": "#FFA500",  # 译文颜色（默认橙黄）
            "original_color": "#FFFFFF",  # 原文颜色（默认白色）
            "translation_outline_color": "#000000",  # 译文描边
            "original_outline_color": "#000000",  # 原文描边
            "line_spacing": 30,  # 行间距（默认值30，可调）
            "translation_margin_v": 80,  # 译文边距（默认值80，从底部向上定位）
            "original_margin_v": 30,  # 原文边距（默认值30，用户可调整）
        }
    )

    # 导出配置
    default_export_format: str = "srt"
    default_encoding: str = "utf-8"

    # 导出路径配置（空字符串表示使用原视频所在文件夹）
    export_path: str = ""  # 自定义导出路径，默认为空
    export_subtitle_path: str = ""  # 字幕导出路径，默认为空
    use_source_folder: bool = True  # 是否使用原文件所在文件夹作为导出位置
    video_filename_prefix: str = "【阿泽】"  # 压制视频文件名前缀

    # 路径配置
    temp_dir: str = "temp"
    output_dir: str = "output"

    # UI 配置
    theme: str = "light"

    def __post_init__(self):
        """初始化后处理"""
        # 加载环境变量
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # 从环境变量覆盖
        if os.getenv("SILICONFLOW_API_KEY"):
            self.api_key = os.getenv("SILICONFLOW_API_KEY")
        if os.getenv("API_BASE_URL"):
            self.api_base_url = os.getenv("API_BASE_URL")

        # 确保路径是绝对路径
        base_dir = Path(__file__).parent.parent
        self.temp_dir = str(base_dir / self.temp_dir)
        self.output_dir = str(base_dir / self.output_dir)

        # 设置默认 FFmpeg 路径
        ffmpeg_bin_dir = base_dir.parent / "ffmpeg" / "ffmpeg-master-latest-win64-gpl" / "bin"
        if not self.ffmpeg_path:
            self.ffmpeg_path = str(ffmpeg_bin_dir / "ffmpeg.exe")
        if not self.ffprobe_path:
            self.ffprobe_path = str(ffmpeg_bin_dir / "ffprobe.exe")

        # 创建目录
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    def save(self, config_path: Optional[str] = None):
        """保存配置到文件"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """从文件加载配置"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"

        config = cls()

        if not Path(config_path).exists():
            logger.info(f"配置文件不存在，使用默认配置: {config_path}")
            return config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 更新配置
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            logger.info(f"配置已从 {config_path} 加载")
        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")

        return config

    def update(self, **kwargs):
        """更新配置"""
        # 键名映射表 (camelCase -> snake_case)
        key_mapping = {
            "apiKey": "api_key",
            "apiModel": "api_model",
            "apiBaseUrl": "api_base_url",
            "vadSensitivity": "vad_sensitivity",
            "vadThreshold": "vad_threshold",
            "vadMinVolumeDb": "vad_min_volume_db",
            "vadEnableVolumeFilter": "vad_enable_volume_filter",
            "minSpeechDuration": "min_speech_duration",
            "minSilenceDuration": "min_silence_duration",
            "maxSpeechDuration": "max_speech_duration",
            "mergeThreshold": "merge_threshold",
            "maxSubtitleLength": "max_subtitle_length",
            "enableMaxSubtitleLength": "enable_max_subtitle_length",
            "asrLanguage": "asr_language",
            "languageGuard": "language_guard",
            "autoRemoveDrift": "auto_remove_drift",
            "contextRetry": "context_retry",
            "contextRetryPadding": "context_retry_padding",
            "translationModel": "translation_model",
            "translationTargetLang": "translation_target_lang",
            "customTranslationModels": "custom_translation_models",
            "translationBatchSize": "translation_batch_size",
            "translationMaxWorkers": "translation_max_workers",
            "subtitleStyle": "subtitle_style",
            "defaultExportFormat": "default_export_format",
            "maxConcurrentTasks": "max_concurrent_tasks",
            "exportPath": "export_path",
            "exportSubtitlePath": "export_subtitle_path",
            "useSourceFolder": "use_source_folder",
            "videoFilenamePrefix": "video_filename_prefix",
            "ttsModel": "tts_model",
            "ttsVoiceName": "tts_voice_name",
            "ttsBatchSize": "tts_batch_size",
            "ttsMaxWorkers": "tts_max_workers",
        }

        for key, value in kwargs.items():
            # 尝试映射键名
            target_key = key_mapping.get(key, key)

            if hasattr(self, target_key):
                setattr(self, target_key, value)
                logger.debug(f"配置更新: {target_key} = {value}")
            else:
                logger.warning(f"未知配置项: {key} (映射后: {target_key})")


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.load()
    return _config_instance


def reload_config() -> Config:
    """重新加载配置"""
    global _config_instance
    _config_instance = Config.load()
    return _config_instance
