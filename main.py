import os
import asyncio
import logging
import aiofiles
import aiohttp
import random
import uuid
import mimetypes
from typing import List, Optional, AsyncGenerator
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.event.filter import (
    event_message_type,
    EventMessageType,
    llm_tool,
    command,
)
from astrbot.api.message_components import *
from astrbot.api import logger

file_lock = asyncio.Lock()

# 栗次元(t.alcy.cc) 全部 17 个分类,完整映射见 https://t.alcy.cc/
# ponytail: dict 化以便用 key 过滤 enabled_categories 配置
CATEGORIES: dict[str, tuple[str, str]] = {
    "ycy":   ("银次缘",   "https://t.alcy.cc/ycy"),
    "moez":  ("萌版自适应", "https://t.alcy.cc/moez"),
    "ai":    ("AI 自适应",  "https://t.alcy.cc/ai"),
    "ysz":   ("原神自适应", "https://t.alcy.cc/ysz"),
    "pc":    ("PC 横图",   "https://t.alcy.cc/pc"),
    "moe":   ("萌版横图",  "https://t.alcy.cc/moe"),
    "fj":    ("风景横图",  "https://t.alcy.cc/fj"),
    "bd":    ("白底横图",  "https://t.alcy.cc/bd"),
    "ys":    ("原神横图",  "https://t.alcy.cc/ys"),
    "acg":   ("ACG 动图",  "https://t.alcy.cc/acg"),
    "mp":    ("移动竖图",  "https://t.alcy.cc/mp"),
    "moemp": ("萌版竖图",  "https://t.alcy.cc/moemp"),
    "ysmp":  ("原神竖图",  "https://t.alcy.cc/ysmp"),
    "aimp":  ("AI 竖图",   "https://t.alcy.cc/aimp"),
    "tx":    ("头像方图",  "https://t.alcy.cc/tx"),
    "lai":   ("七濑胡桃",  "https://t.alcy.cc/lai"),
    "xhl":   ("小狐狸",    "https://t.alcy.cc/xhl"),
}

ALLOWED_IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
}


class ImageManager:
    """图片管理类(原样保留自上游)"""

    def __init__(self):
        self.imgs_folder = "imgs"
        self.supported_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
        self._init_folder()

    def _init_folder(self):
        if not os.path.exists(self.imgs_folder):
            os.makedirs(self.imgs_folder)
            logger.info("Created images folder")

    async def get_image_list(self):
        async with file_lock:
            try:
                files = await asyncio.to_thread(os.listdir, self.imgs_folder)
                return [f for f in files if os.path.splitext(f)[1].lower() in self.supported_extensions]
            except Exception as e:
                logger.error(f"Error getting image list: {str(e)}")
                return []

    async def delete_image(self, filename: str):
        async with file_lock:
            file_path = os.path.join(self.imgs_folder, filename)
            try:
                if os.path.exists(file_path):
                    await asyncio.to_thread(os.remove, file_path)
                    logger.info(f"Deleted image: {filename}")
                    return True
                logger.warning(f"Attempted to delete non-existent file: {filename}")
                return False
            except Exception as e:
                logger.error(f"Error deleting image {filename}: {str(e)}")
                return False

    async def generate_and_save_image(self, url) -> Optional[str]:
        async with file_lock:
            try:
                timeout = aiohttp.ClientTimeout(total=20, connect=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, allow_redirects=True, max_redirects=5) as response:
                        response.raise_for_status()
                        content_type = response.headers.get("Content-Type", "").lower()
                        if content_type not in ALLOWED_IMAGE_MIMES:
                            logger.error(f"Invalid Content-Type: {content_type}")
                            return None
                        ext = mimetypes.guess_extension(content_type)
                        if not ext or ext.lower() not in self.supported_extensions:
                            ext = ".jpg"
                        filename = f"{uuid.uuid4().hex}{ext}"
                        file_path = os.path.join(self.imgs_folder, filename)
                        content = await response.read()
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        logger.info(f"Saved image: {filename}, {len(content)} bytes")
                        return filename
            except aiohttp.ClientError as e:
                logger.error(f"HTTP Request Failed for {url}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error saving image from {url}: {str(e)}")
                return None


image_manager = ImageManager()


@register(
    "astrbot_plugin_Pic",
    "ImNotBird / publieople",
    "随机看图(栗次元为主),支持命令触发、LLM 自动调用、可配置图源开关",
    "v1.8.0",
    "https://github.com/publieople/astrbot_plugin_Pic",
)
class ImagePlugin(Star):
    def __init__(self, context: Context, config: Optional[dict] = None):
        super().__init__(context)
        self.image_manager = image_manager
        self.config = config or {}
        self.max_retries = int(self.config.get("max_retries", 2))
        self.trigger_words = [w.strip() for w in self.config.get("trigger_words", "我要看图").split(",") if w.strip()]
        # enabled_categories 为空 => 全启用;否则只保留学员勾的 key
        enabled_keys = self.config.get("enabled_categories") or list(CATEGORIES.keys())
        self.enabled_urls = [CATEGORIES[k][1] for k in enabled_keys if k in CATEGORIES]

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent) -> MessageEventResult:
        """关键词触发:消息里出现触发词就随机一张图"""
        try:
            text = event.message_str.lower()
            if any(w.lower() in text for w in self.trigger_words):
                await event.send(event.plain_result("好的,正在为你准备图片..."))
                return await self.handle_image_request(event)
        except Exception as e:
            logger.error(f"Message handler error: {str(e)}")
            return event.plain_result(f"插件异常: {str(e)}")

    @command("看图分类")
    async def cmd_list_sources(self, event: AstrMessageEvent):
        """看图分类 - 列出当前已启用的图源"""
        lines = ["当前启用的图源:"]
        for i, url in enumerate(self.enabled_urls, 1):
            lines.append(f"  {i:2d}. {url}")
        yield event.plain_result("\n".join(lines))

    @llm_tool(name="send_random_pic")
    async def llm_send_random_pic(self, event: AstrMessageEvent):
        """给当前对话的用户发送一张随机图片。当对话氛围合适、用户可能想看图,或你被要求配图时调用。

        每次只发一张,不要重复调用。
        """
        result = await self.handle_image_request(event)
        # 工具要返回字符串给 LLM 汇总;event.send 已经把图片发出去了
        return "已发送一张随机图片"

    async def handle_image_request(self, event: AstrMessageEvent) -> MessageEventResult:
        try:
            failed_urls = set()
            filename = None
            for attempt in range(self.max_retries + 1):
                available_urls = [u for u in self.enabled_urls if u not in failed_urls]
                if not available_urls:
                    break
                selected = random.choice(available_urls)
                logger.info(f"Attempt {attempt+1}: {selected}")
                filename = await self.image_manager.generate_and_save_image(selected)
                if filename:
                    break
                failed_urls.add(selected)
            if not filename:
                return event.plain_result(f"所有图源都获取失败了(已重试{self.max_retries}次)")
            image_path = os.path.join(self.image_manager.imgs_folder, filename)
            message_chain = event.make_result().file_image(image_path)
            try:
                await event.send(message_chain)
                await asyncio.sleep(1)
                deleted = await self.image_manager.delete_image(filename)
                return event.plain_result("图片已送达" if deleted else "图片已发送,缓存清理有点小问题")
            except Exception as e:
                logger.warning(f"Send image failed: {e}")
                await self.image_manager.delete_image(filename)
                return event.plain_result("网络波动,图片发送失败")
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            return event.plain_result("处理请求时发生错误")

    async def terminate(self):
        try:
            image_files = await self.image_manager.get_image_list()
            if image_files:
                await asyncio.gather(*(self.image_manager.delete_image(f) for f in image_files))
            logger.info("Plugin terminated, cleaned up %d cached images", len(image_files))
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
