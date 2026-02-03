import os
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

from core.task_manager import TaskManager, TaskStatus
from core.audio_processor import AudioProcessor
from core.vad_processor import VADProcessor
from core.sensevoice_client import SenseVoiceClient
from core.subtitle_generator import SubtitleGenerator
from core.translation_client import TranslationClient
from core.tts_client import TTSClient
from core.video_synthesizer import VideoSynthesizer
from utils.logger import setup_logger, get_logger
from utils.config import get_config

# 初始化日志
setup_logger()
logger = get_logger("app")

# 获取配置
config = get_config()

# 初始化 Flask 和 SocketIO
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "video-subtitle-secret")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# 初始化核心组件
task_manager = TaskManager()
audio_processor = AudioProcessor()
vad_processor = VADProcessor()
sensevoice_client = SenseVoiceClient(
    api_key=config.api_key, base_url=config.api_base_url, model=config.api_model
)
subtitle_generator = SubtitleGenerator()
translation_client = TranslationClient()
tts_client = TTSClient()
video_synthesizer = VideoSynthesizer()

# 任务房间映射 (task_id -> sid)
task_rooms: Dict[str, str] = {}


def init_app():
    """初始化应用"""
    logger.info("正在初始化应用...")

    # 确保必要目录存在
    Path(config.temp_dir).mkdir(parents=True, exist_ok=True)
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    # 注册进度回调
    task_manager.set_progress_callback(on_task_progress)

    logger.info("应用初始化完成")


def on_task_progress(task_id: str, progress: float, status_text: str, data: Any = None):
    """任务进度回调"""
    # 发送进度更新到对应房间
    socketio.emit(
        "task_progress",
        {
            "taskId": task_id,
            "progress": progress,
            "statusText": status_text,
            "status": TaskStatus.PROCESSING.value,
            "data": data,
        },
        room=task_id,
    )


def process_video_task(task_id: str):
    """异步处理视频任务"""
    task = task_manager.get_task(task_id)
    if not task:
        logger.error(f"任务 {task_id} 不存在")
        return

    try:
        # 1. 提取音频
        task_manager.update_task_status(
            task_id, TaskStatus.PROCESSING, 5, "正在提取音频..."
        )
        audio_path = audio_processor.extract_audio(task.file_path)
        task.audio_path = audio_path

        # 2. VAD 语音检测
        task_manager.update_task_status(
            task_id, TaskStatus.PROCESSING, 15, "正在检测语音段落..."
        )
        voice_segments = vad_processor.process(audio_path)

        if not voice_segments:
            raise Exception("未检测到语音内容")

        # 3. 语音识别 (ASR)
        task_manager.update_task_status(
            task_id, TaskStatus.PROCESSING, 25, f"正在识别语音 ({len(voice_segments)} 段)..."
        )

        # 分块识别
        transcription_results = sensevoice_client.transcribe_segments(
            audio_path,
            voice_segments,
            language=config.asr_language,
            on_progress=lambda p: task_manager.update_task_status(
                task_id, TaskStatus.PROCESSING, 25 + p * 0.4, "正在识别语音..."
            ),
        )

        # 4. 生成原始字幕
        task_manager.update_task_status(
            task_id, TaskStatus.PROCESSING, 65, "正在生成字幕..."
        )
        subtitles = subtitle_generator.generate_from_asr(transcription_results)
        task.subtitles = subtitles

        # 5. 任务完成
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED, 100, "处理完成")
        logger.info(f"任务 {task_id} 处理成功")

    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {e}")
        task_manager.update_task_status(task_id, TaskStatus.FAILED, 0, f"错误: {str(e)}")


@app.route("/api/translate", methods=["POST"])
def translate_subtitles():
    """翻译字幕"""
    try:
        data = request.get_json()

        if not data or "taskId" not in data:
            return jsonify({"success": False, "error": "缺少 taskId 参数"}), 400

        task_id = data["taskId"]
        target_lang = data.get("targetLang", config.translation_target_lang)

        task = task_manager.get_task(task_id)

        if not task:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        if not task.subtitles:
            return jsonify({"success": False, "error": "任务没有字幕数据"}), 400

        # 更新状态
        task_manager.update_task_status(task_id, TaskStatus.PROCESSING, 70, "正在翻译字幕...")

        # 准备翻译文本
        texts = [s["text"] for s in task.subtitles]

        # 调用翻译客户端
        translated_texts = translation_client.translate_batch(
            texts,
            target_lang=target_lang,
            on_progress=lambda p: task_manager.update_task_status(
                task_id, TaskStatus.PROCESSING, 70 + p * 0.2, "正在翻译字幕..."
            ),
        )

        # 更新任务字幕
        for i, text in enumerate(translated_texts):
            task.subtitles[i]["translation"] = text

        # 更新状态
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED, 100, "翻译完成")

        return jsonify(
            {
                "success": True,
                "data": task.to_dict(),
                "message": "翻译成功",
            }
        )

    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/run-dubbing", methods=["POST"])
def run_dubbing():
    """运行配音与合成"""
    try:
        data = request.get_json()

        if not data or "taskId" not in data:
            return jsonify({"success": False, "error": "缺少 taskId 参数"}), 400

        task_id = data["taskId"]
        options = data.get("options", {})

        task = task_manager.get_task(task_id)

        if not task:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        # 启动异步配音任务
        threading.Thread(target=_process_dubbing, args=(task_id, options)).start()

        return jsonify(
            {
                "success": True,
                "message": "配音任务已启动",
            }
        )

    except Exception as e:
        logger.error(f"启动配音失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _process_dubbing(task_id: str, options: dict):
    """处理配音与合成的内部逻辑"""
    task = task_manager.get_task(task_id)
    if not task:
        return

    temp_files = []

    try:
        # 1. TTS 语音合成
        task_manager.update_task_status(task_id, TaskStatus.PROCESSING, 10, "正在合成配音...")

        # 使用翻译文本进行配音，如果没有翻译则使用原文
        dubbing_segments = []
        for s in task.subtitles:
            text = s.get("translation") or s.get("text")
            if text:
                dubbing_segments.append(
                    {
                        "id": s["id"],
                        "text": text,
                        "start": s["startTime"],
                        "end": s["endTime"],
                    }
                )

        if not dubbing_segments:
            raise Exception("没有可用于配音的文本内容")

        # 调用 TTS 客户端
        audio_segments = tts_client.generate_batch(
            dubbing_segments,
            voice_name=options.get("voiceName", config.tts_voice_name),
            on_progress=lambda p: task_manager.update_task_status(
                task_id, TaskStatus.PROCESSING, 10 + p * 0.4, "正在合成配音..."
            ),
        )

        # 2. 视频合成 (压制字幕 + 替换音频)
        task_manager.update_task_status(task_id, TaskStatus.PROCESSING, 60, "正在合成视频...")

        # 准备输出路径
        # 去除前缀两端的空格，如果未设置则不使用前缀
        prefix = config.video_filename_prefix.strip() if config.video_filename_prefix else ""
        original_stem = Path(task.file_path).stem
        output_name = f"{prefix}{original_stem}_人声配音版.mp4"

        # 增加对自定义路径有效性的验证，如果路径不可写或无效，则回退
        export_dir = None
        if config.export_path and config.export_path.strip():
            try:
                temp_dir = Path(config.export_path.strip())
                # 尝试创建目录以验证有效性
                temp_dir.mkdir(parents=True, exist_ok=True)
                # 检查是否可写
                test_file = temp_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
                export_dir = temp_dir
                logger.info(f"使用验证通过的自定义导出路径: {export_dir}")
            except Exception as e:
                logger.warning(f"自定义导出路径 {config.export_path} 无效或不可写: {e}，将回退")

        if not export_dir:
            if config.use_source_folder and task.file_path:
                export_dir = Path(task.file_path).parent
                logger.info(f"回退到原视频所在目录: {export_dir}")
            else:
                export_dir = Path(config.output_dir)
                logger.info(f"回退到默认输出目录: {export_dir}")

        export_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(export_dir / output_name)

        # 压制参数
        synthesize_options = {
            "subtitles": task.subtitles,
            "audio_segments": audio_segments,
            "subtitle_style": config.subtitle_style,
            "bilingual": options.get("bilingual", False),
            "original_audio_volume": options.get("originalAudioVolume", 0.1),
            "dubbing_volume": options.get("dubbingVolume", 1.0),
        }

        # 调用合成引擎
        result_path = video_synthesizer.synthesize(
            task.file_path,
            output_path,
            **synthesize_options,
            on_progress=lambda p: task_manager.update_task_status(
                task_id, TaskStatus.PROCESSING, 60 + p * 0.35, "正在合成视频..."
            ),
        )

        task.output_video_path = result_path

        # 3. 清理预览图 (清理 temp_dir 下所有预览图)
        try:
            temp_dir_path = Path(config.temp_dir)
            for f in temp_dir_path.glob("preview_*.png"):
                f.unlink(missing_ok=True)
            logger.info("已清理所有临时预览图")
        except Exception as pe:
            logger.debug(f"清理预览图失败: {pe}")

        # 4. 完成
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED, 100, "配音合成完成")
        logger.info(f"任务 {task_id} 配音合成成功: {result_path}")

    except Exception as e:
        logger.error(f"任务 {task_id} 配音合成失败: {e}")
        task_manager.update_task_status(task_id, TaskStatus.FAILED, 0, f"错误: {str(e)}")

    finally:
        # 清理临时文件
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


@app.route("/api/preview-subtitle", methods=["POST"])
def preview_subtitle():
    """预览字幕样式"""
    try:
        data = request.get_json()

        if not data or "filePath" not in data:
            return jsonify({"success": False, "error": "缺少 filePath 参数"}), 400

        file_path = data["filePath"]
        style = data.get("style", config.subtitle_style)
        text = data.get("text", "这是预览字幕效果 This is a preview subtitle")
        timestamp = data.get("timestamp", 1.0)

        # 生成预览图
        preview_id = f"preview_{int(time.time())}"
        preview_path = Path(config.temp_dir) / f"{preview_id}.png"

        result_path = video_synthesizer.generate_preview(
            file_path, str(preview_path), text, style, timestamp
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "previewUrl": f"/api/temp/{preview_id}.png",
                    "previewPath": result_path,
                },
            }
        )

    except Exception as e:
        logger.error(f"生成预览失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/temp/<path:filename>")
def serve_temp(filename):
    """提供临时文件访问"""
    return send_from_directory(config.temp_dir, filename)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    """创建新任务"""
    try:
        data = request.get_json()

        if not data or "filePath" not in data:
            return jsonify({"success": False, "error": "缺少 filePath 参数"}), 400

        file_path = data["filePath"]
        file_name = data.get("fileName")
        file_size = data.get("fileSize")

        if not Path(file_path).exists():
            return jsonify({"success": False, "error": f"文件不存在: {file_path}"}), 400

        # 创建任务
        task = task_manager.create_task(file_path)

        # 更新任务信息
        task.file_name = file_name or task.file_name
        task.file_size = file_size or task.file_size

        logger.info(f"API创建任务: {task.id} - {task.file_name}")

        # 启动异步处理
        threading.Thread(target=process_video_task, args=(task.id,)).start()

        return jsonify({"success": True, "data": task.to_dict()})

    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """获取任务详情"""
    try:
        task = task_manager.get_task(task_id)

        if not task:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        return jsonify({"success": True, "data": task.to_dict()})

    except Exception as e:
        logger.error(f"获取任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """删除任务"""
    try:
        success = task_manager.delete_task(task_id)

        if not success:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        return jsonify({"success": True, "message": "任务已删除"})

    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tasks/<task_id>/retry", methods=["POST"])
def retry_task(task_id):
    """重试任务"""
    try:
        task = task_manager.get_task(task_id)

        if not task:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        # 重置状态
        task_manager.update_task_status(task_id, TaskStatus.PENDING, 0, "等待重试")

        # 启动异步处理
        threading.Thread(target=process_video_task, args=(task_id,)).start()

        return jsonify({"success": True, "data": task.to_dict()})

    except Exception as e:
        logger.error(f"重试任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tasks", methods=["GET"])
def get_all_tasks():
    """获取所有任务"""
    try:
        tasks = task_manager.get_all_tasks()

        return jsonify({"success": True, "data": [task.to_dict() for task in tasks]})

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def export_subtitles():
    """导出字幕"""
    try:
        data = request.get_json()

        if not data or "taskId" not in data:
            return jsonify({"success": False, "error": "缺少 taskId 参数"}), 400

        task_id = data["taskId"]
        export_format = data.get("format", "srt")
        output_path = data.get("outputPath")
        include_timestamp = data.get("includeTimestamp", False)

        task = task_manager.get_task(task_id)

        if not task:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        if not task.subtitles:
            return jsonify({"success": False, "error": "任务没有字幕数据"}), 400

        # 生成输出路径（根据配置确定导出目录）
        if not output_path:
            if config.export_subtitle_path and config.export_subtitle_path.strip():
                # 使用用户自定义的字幕导出路径
                output_dir = Path(config.export_subtitle_path)
            elif config.export_path and config.export_path.strip():
                # 使用统一的导出路径
                output_dir = Path(config.export_path)
            elif config.use_source_folder and task.file_path:
                # 使用原视频所在文件夹
                output_dir = Path(task.file_path).parent
            else:
                # 使用默认输出目录
                output_dir = Path(config.output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{task.file_name}.{export_format}"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换字幕格式
        segments = [
            {
                "id": s["id"],
                "start": s["startTime"],
                "end": s["endTime"],
                "text": s["text"],
            }
            for s in task.subtitles
        ]

        # 导出
        result_path = subtitle_generator.export_subtitles(
            segments,
            str(output_path),
            format=export_format,
            include_timestamp=include_timestamp,
        )

        logger.info(f"导出字幕: {result_path}")

        return jsonify(
            {
                "success": True,
                "data": {"filePath": result_path, "format": export_format},
                "message": "导出成功",
            }
        )

    except Exception as e:
        logger.error(f"导出字幕失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """获取配置"""
    try:
        return jsonify({"success": True, "data": config.to_dict()})
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def save_settings():
    """保存配置"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "缺少配置数据"}), 400

        mapping = {
            "apiKey": "api_key",
            "vadSensitivity": "vad_sensitivity",
            "minSilenceDuration": "min_silence_duration",
            "mergeThreshold": "merge_threshold",
            "defaultExportFormat": "default_export_format",
            "maxConcurrentTasks": "max_concurrent_tasks",
            "asrLanguage": "asr_language",
            "maxSubtitleLength": "max_subtitle_length",
            "enableMaxSubtitleLength": "enable_max_subtitle_length",
            "maxSpeechDuration": "max_speech_duration",
            "languageGuard": "language_guard",
            "autoRemoveDrift": "auto_remove_drift",
            "contextRetry": "context_retry",
            "contextRetryPadding": "context_retry_padding",
            "apiBaseUrl": "api_base_url",
            "apiModel": "api_model",
            "translationModel": "translation_model",
            "translationTargetLang": "translation_target_lang",
            "customTranslationModels": "custom_translation_models",
            "translationBatchSize": "translation_batch_size",
            "translationMaxWorkers": "translation_max_workers",
            "ttsMaxWorkers": "tts_max_workers",
            "subtitleStyle": "subtitle_style",
            "exportPath": "export_path",
            "exportSubtitlePath": "export_subtitle_path",
            "useSourceFolder": "use_source_folder",
            "videoFilenamePrefix": "video_filename_prefix",
        }

        if "tts_max_workers" in data:
            try:
                data["tts_max_workers"] = max(1, min(10, int(data["tts_max_workers"])))
            except Exception:
                data.pop("tts_max_workers", None)

        for camel, snake in mapping.items():
            if camel in data and snake not in data:
                data[snake] = data[camel]

        if "max_concurrent_tasks" in data:
            try:
                data["max_concurrent_tasks"] = max(
                    1, min(20, int(data["max_concurrent_tasks"]))
                )
            except Exception:
                data.pop("max_concurrent_tasks", None)

        if "vad_sensitivity" in data:
            try:
                data["vad_sensitivity"] = max(
                    0.1, min(0.9, float(data["vad_sensitivity"]))
                )
            except Exception:
                data.pop("vad_sensitivity", None)

        if "min_silence_duration" in data:
            try:
                data["min_silence_duration"] = max(
                    0.01, min(2.0, float(data["min_silence_duration"]))
                )
            except Exception:
                data.pop("min_silence_duration", None)

        if "merge_threshold" in data:
            try:
                data["merge_threshold"] = max(
                    0.0, min(2.0, float(data["merge_threshold"]))
                )
            except Exception:
                data.pop("merge_threshold", None)

        if "max_subtitle_length" in data:
            try:
                data["max_subtitle_length"] = max(
                    5, min(200, int(data["max_subtitle_length"]))
                )
            except Exception:
                data.pop("max_subtitle_length", None)

        if "max_speech_duration" in data:
            try:
                data["max_speech_duration"] = max(
                    1.0, min(60.0, float(data["max_speech_duration"]))
                )
            except Exception:
                data.pop("max_speech_duration", None)

        if "context_retry_padding" in data:
            try:
                data["context_retry_padding"] = max(
                    0.0, min(1.0, float(data["context_retry_padding"]))
                )
            except Exception:
                data.pop("context_retry_padding", None)

        if "translation_batch_size" in data:
            try:
                data["translation_batch_size"] = max(
                    1, min(100, int(data["translation_batch_size"]))
                )
            except Exception:
                data.pop("translation_batch_size", None)

        if "translation_max_workers" in data:
            try:
                data["translation_max_workers"] = max(
                    1, min(10, int(data["translation_max_workers"]))
                )
            except Exception:
                data.pop("translation_max_workers", None)

        if "tts_max_workers" in data:
            try:
                data["tts_max_workers"] = max(1, min(20, int(data["tts_max_workers"])))
                logger.info(f"设置 tts_max_workers 为: {data['tts_max_workers']}")
            except Exception:
                data.pop("tts_max_workers", None)

        for key in (
            "language_guard",
            "context_retry",
            "auto_remove_drift",
            "enable_max_subtitle_length",
            "use_source_folder",
        ):
            if key in data:
                val = data[key]
                if isinstance(val, str):
                    data[key] = val.strip().lower() in ("1", "true", "yes", "on")
                elif not isinstance(val, bool):
                    data[key] = bool(val)

        # 更新配置
        config.update(**data)

        logger.info(f"配置更新完成，关键配置项：")
        logger.info(f"  - tts_max_workers: {config.tts_max_workers}")
        logger.info(f"  - export_path: {config.export_path}")
        logger.info(f"  - use_source_folder: {config.use_source_folder}")

        if "max_concurrent_tasks" in data:
            task_manager.set_max_concurrent(data["max_concurrent_tasks"])

        # 如果更新了 API Key，同步更新 SenseVoice 客户端
        if "api_key" in data:
            sensevoice_client.api_key = data["api_key"]
            logger.info("API Key 已更新并同步到语音识别客户端")
        if "api_model" in data:
            sensevoice_client.model = data["api_model"]

        # 保存到文件
        config.save()

        logger.info("配置已更新")

        return jsonify(
            {"success": True, "data": config.to_dict(), "message": "配置已保存"}
        )

    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/check-api-key", methods=["POST"])
def check_api_key():
    """检查 API Key"""
    try:
        data = request.get_json()
        api_key = data.get("apiKey", "") if data else ""

        # 如果提供了 API Key，先更新配置
        if api_key:
            config.api_key = api_key
            sensevoice_client.api_key = api_key
            logger.info("API Key 已更新")

        # 验证 API Key
        is_valid = sensevoice_client.check_api_key()

        if is_valid and api_key:
            # 验证成功，保存配置
            config.save()
            logger.info("API Key 验证成功，配置已保存")

        return jsonify({"success": True, "data": {"valid": is_valid}})

    except Exception as e:
        logger.error(f"检查 API Key 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """上传视频文件"""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "没有文件"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "文件名空"}), 400

        # 保存到临时目录
        from werkzeug.utils import secure_filename

        filename = secure_filename(file.filename)
        upload_dir = Path(config.temp_dir) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filepath = upload_dir / filename
        file.save(str(filepath))

        logger.info(f"文件上传成功: {filepath}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "filePath": str(filepath),
                    "fileName": filename,
                    "fileSize": filepath.stat().st_size,
                },
                "message": "文件上传成功",
            }
        )

    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/video-info", methods=["POST"])
def get_video_info():
    """获取视频信息"""
    try:
        data = request.get_json()

        if not data or "filePath" not in data:
            return jsonify({"success": False, "error": "缺少 filePath 参数"}), 400

        file_path = data["filePath"]

        if not Path(file_path).exists():
            return jsonify({"success": False, "error": f"文件不存在: {file_path}"}), 400

        # 获取视频时长
        duration = audio_processor.get_video_duration(file_path)

        return jsonify(
            {
                "success": True,
                "data": {
                    "filePath": file_path,
                    "fileName": Path(file_path).name,
                    "duration": duration,
                },
            }
        )

    except Exception as e:
        logger.error(f"获取视频信息失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== WebSocket Events ====================


@socketio.on("connect")
def handle_connect():
    """客户端连接"""
    logger.debug(f"客户端已连接: {request.sid}")
    emit("connected", {"status": "connected", "timestamp": int(time.time() * 1000)})


@socketio.on("disconnect")
def handle_disconnect():
    """客户端断开"""
    logger.debug(f"客户端已断开: {request.sid}")

    # 清理房间映射
    rooms_to_remove = []
    for task_id, sid in task_rooms.items():
        if sid == request.sid:
            rooms_to_remove.append(task_id)

    for task_id in rooms_to_remove:
        del task_rooms[task_id]


@socketio.on("join_task")
def handle_join_task(data):
    """加入任务房间"""
    task_id = data.get("taskId")

    if not task_id:
        emit("error", {"message": "缺少 taskId"})
        return

    join_room(task_id)
    task_rooms[task_id] = request.sid

    logger.debug(f"客户端 {request.sid} 加入任务房间: {task_id}")

    # 发送当前任务状态
    task = task_manager.get_task(task_id)
    if task:
        emit("task_status", task.to_dict())


@socketio.on("leave_task")
def handle_leave_task(data):
    """离开任务房间"""
    task_id = data.get("taskId")

    if task_id:
        leave_room(task_id)
        task_rooms.pop(task_id, None)
        logger.debug(f"客户端 {request.sid} 离开任务房间: {task_id}")


@socketio.on("subscribe_progress")
def handle_subscribe_progress(data):
    """订阅进度更新"""
    task_id = data.get("taskId")

    if task_id:
        join_room(task_id)
        task_rooms[task_id] = request.sid
        emit("subscribed", {"taskId": task_id})


# ==================== Error Handlers ====================


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "接口不存在"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"服务器错误: {error}")
    return jsonify({"success": False, "error": "服务器内部错误"}), 500


# ==================== Main ====================

if __name__ == "__main__":
    init_app()

    # 启动服务器
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"启动服务器: http://0.0.0.0:{port}")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=False,
        log_output=False,
        allow_unsafe_werkzeug=True,
    )
