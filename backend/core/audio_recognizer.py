"""统一音频识别接口 - 仅支持API模式"""

from typing import Optional, Callable, Dict

from utils.logger import get_logger
from core.sensevoice_client import SenseVoiceClient

logger = get_logger("audio_recognizer")


class AudioRecognizer:
    """
    统一音频识别接口 - 仅支持云端API模式
    """

    def __init__(self):
        self.api_client = SenseVoiceClient()
        logger.info("音频识别器初始化完成（API模式）")

    def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            language: 语言代码 (zh, en, ja, ko等)
            progress_callback: 进度回调函数

        Returns:
            转录结果 {"text": "识别的文本"}
        """
        logger.info(f"使用云端API转录: {audio_path}")
        return self.api_client.transcribe(audio_path, language, progress_callback)


# 单例模式
_recognizer_instance: Optional[AudioRecognizer] = None


def get_recognizer() -> AudioRecognizer:
    """获取识别器单例"""
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = AudioRecognizer()
    return _recognizer_instance
