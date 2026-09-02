"""
AI 模型调用服务
支持 OpenAI / DeepSeek / 任何 OpenAI 兼容 API
"""
import json
from typing import AsyncGenerator, List, Optional
import httpx
from loguru import logger
from app.config import Config


# 搜索场景的 AI 系统提示词
SEARCH_SYSTEM_PROMPT = """你是一个TG频道消息搜索助手。用户输入关键词，你的任务：
1. 分析用户意图，理解搜索需求
2. 扩展相关关键词（最多5个同义词/相关词）
3. 提供简短的搜索建议

输出格式（JSON）：
{"main_keyword":"主关键词","related_keywords":["词1","词2","词3","词4","词5"],"search_hint":"搜索建议"}
只输出JSON，不要有其他内容。"""

# 聊天场景的 AI 系统提示词
CHAT_SYSTEM_PROMPT = """你是一个TG频道消息知识库问答助手。用户可以向你提问关于TG频道内容的任何问题，你会根据已有的搜索知识库帮助用户解答。"""


class AIService:
    """AI 模型调用服务"""

    def __init__(self):
        self.provider = "deepseek"
        self.api_base = "https://api.deepseek.com"
        self.api_key = ""
        self.model = "deepseek-chat"
        self.max_tokens = 1024
        self.temperature = 0.7
        self.keyword_expand = True
        self.summarize_results = True
        self.free_daily_limit = 3
        self.search_system_prompt = SEARCH_SYSTEM_PROMPT
        self.chat_system_prompt = CHAT_SYSTEM_PROMPT
        self._load_from_config()

    def _load_from_config(self):
        """从 Config 加载 AI 配置"""
        self.provider = getattr(Config, "AI_PROVIDER", "deepseek") or "deepseek"
        self.api_base = getattr(Config, "AI_API_BASE", "https://api.deepseek.com") or "https://api.deepseek.com"
        self.api_key = getattr(Config, "AI_API_KEY", "") or ""
        self.model = getattr(Config, "AI_MODEL", "deepseek-chat") or "deepseek-chat"
        self.max_tokens = getattr(Config, "AI_MAX_TOKENS", 1024) or 1024
        self.temperature = getattr(Config, "AI_TEMPERATURE", 0.7) or 0.7
        self.keyword_expand = getattr(Config, "AI_KEYWORD_EXPAND", True)
        self.summarize_results = getattr(Config, "AI_SUMMARIZE_RESULTS", True)
        self.free_daily_limit = getattr(Config, "AI_FREE_DAILY_LIMIT", 3) or 3

    async def load_from_db(self):
        """从数据库加载配置并覆盖"""
        try:
            from app.ai.settings_manager import get_ai_config
            cfg = await get_ai_config()
            if cfg.get("AI_PROVIDER"):
                self.provider = cfg["AI_PROVIDER"]
            if cfg.get("AI_API_BASE"):
                self.api_base = cfg["AI_API_BASE"]
            if cfg.get("AI_API_KEY"):
                self.api_key = cfg["AI_API_KEY"]
            if cfg.get("AI_MODEL"):
                self.model = cfg["AI_MODEL"]
            if cfg.get("AI_MAX_TOKENS"):
                self.max_tokens = int(cfg["AI_MAX_TOKENS"])
            if cfg.get("AI_TEMPERATURE"):
                self.temperature = float(cfg["AI_TEMPERATURE"])
            if cfg.get("AI_KEYWORD_EXPAND") is not None:
                self.keyword_expand = bool(cfg["AI_KEYWORD_EXPAND"])
            if cfg.get("AI_SUMMARIZE_RESULTS") is not None:
                self.summarize_results = bool(cfg["AI_SUMMARIZE_RESULTS"])
            if cfg.get("AI_FREE_DAILY_LIMIT"):
                self.free_daily_limit = int(cfg["AI_FREE_DAILY_LIMIT"])
            if cfg.get("AI_SEARCH_SYSTEM_PROMPT"):
                self.search_system_prompt = cfg["AI_SEARCH_SYSTEM_PROMPT"]
            logger.info(f"AI配置已加载: provider={self.provider}, model={self.model}")
        except Exception as e:
            logger.warning(f"AI配置加载失败: {e}")

    def is_configured(self) -> bool:
        """检查是否配置了 AI API"""
        return bool(self.api_key) and bool(self.api_base)

    async def _call_api(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        调用 OpenAI 兼容 API
        返回: {"content": str, "model": str, "input_tokens": int, "output_tokens": int}
        """
        if not self.is_configured():
            return {"content": "❌ AI 功能未配置，请联系管理员设置 API Key", "model": "", "input_tokens": 0, "output_tokens": 0}

        url = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return {
                    "content": content,
                    "model": data.get("model", self.model),
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"AI API 调用失败: {e.response.status_code} - {e.response.text[:200]}")
                return {
                    "content": f"❌ AI API 调用失败 ({e.response.status_code})，请稍后重试",
                    "model": "",
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            except Exception as e:
                logger.error(f"AI API 调用异常: {e}")
                return {
                    "content": f"❌ AI 服务异常: {str(e)[:100]}",
                    "model": "",
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

    async def expand_keyword(self, keyword: str) -> dict:
        """
        扩展关键词：生成相关关键词和搜索建议
        返回: {"main_keyword": str, "related_keywords": list, "search_hint": str}
        """
        if not self.keyword_expand or not self.is_configured():
            return {
                "main_keyword": keyword,
                "related_keywords": [keyword],
                "search_hint": "",
            }

        messages = [
            {"role": "system", "content": self.search_system_prompt},
            {"role": "user", "content": keyword},
        ]
        result = await self._call_api(messages)
        content = result.get("content", "")

        # 解析 JSON 响应
        expanded = {"main_keyword": keyword, "related_keywords": [keyword], "search_hint": ""}
        try:
            parsed = json.loads(content)
            expanded.update(parsed)
        except (json.JSONDecodeError, TypeError):
            # 如果不是 JSON，直接用原文作为提示
            expanded["search_hint"] = content[:100] if content else ""

        result["expanded"] = expanded
        result["tokens_used"] = result.get("input_tokens", 0) + result.get("output_tokens", 0)
        return result

    async def summarize_search_results(self, keyword: str, results: list) -> str:
        """
        AI 总结搜索结果
        results: [{channel_title, channel_username, excerpt, msg_date}, ...]
        """
        if not self.summarize_results or not self.is_configured():
            return ""
        if not results:
            return ""

        # 截取部分结果用于总结
        preview = []
        for i, item in enumerate(results[:5]):
            channel = item.get("channel_title") or item.get("channel_username") or "未知频道"
            excerpt = (item.get("excerpt") or "")[:80]
            date = item.get("msg_date", "")[:10] if item.get("msg_date") else ""
            preview.append(f"{i+1}. [{channel}] {excerpt} ({date})")

        context = "\n".join(preview)
        messages = [
            {"role": "system", "content": "你是一个信息分析助手。根据以下搜索结果，生成一段简洁的总结（2-3句话），指出主要内容主题和相关频道。"},
            {"role": "user", "content": f"搜索关键词：{keyword}\n\n搜索结果：\n{context}\n\n请生成总结："},
        ]
        result = await self._call_api(messages, max_tokens=256)
        return result.get("content", "")

    async def chat(
        self,
        user_question: str,
        context_results: Optional[list] = None,
    ) -> dict:
        """
        AI 对话：根据知识库回答问题
        返回: {"content": str, "input_tokens": int, "output_tokens": int}
        """
        if not self.is_configured():
            return {
                "content": "❌ AI 功能未配置，请联系管理员设置 API Key",
                "input_tokens": 0,
                "output_tokens": 0,
            }

        context = ""
        if context_results:
            ctx_lines = []
            for i, item in enumerate(context_results[:8]):
                channel = item.get("channel_title") or item.get("channel_username") or "未知"
                excerpt = (item.get("excerpt") or "")[:150]
                ctx_lines.append(f"[{channel}] {excerpt}")
            context = "\n".join(ctx_lines)

        system_msg = self.chat_system_prompt
        if context:
            system_msg += f"\n\n相关的TG频道消息内容：\n{context}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_question},
        ]
        result = await self._call_api(messages, max_tokens=512)
        return result

    async def smart_search(
        self,
        keyword: str,
        results: list,
    ) -> dict:
        """
        智能搜索增强：扩展关键词 + 总结结果
        返回: {
            "original_keyword": str,
            "expanded_keywords": list,
            "summary": str,
            "search_hint": str,
            "result_count": int,
        }
        """
        expanded = await self.expand_keyword(keyword)
        related = expanded.get("related_keywords", [keyword])
        summary = ""
        if self.summarize_results:
            summary = await self.summarize_search_results(keyword, results)

        return {
            "original_keyword": keyword,
            "expanded_keywords": related,
            "summary": summary,
            "search_hint": expanded.get("search_hint", ""),
            "result_count": len(results),
        }


# 全局实例
ai_service = AIService()
