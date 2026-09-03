"""
AI 模型调用服务
支持 OpenAI / DeepSeek / 任何 OpenAI 兼容 API
支持多 API 池 + 自动故障切换
"""
import json
import threading
from typing import AsyncGenerator, List, Optional
import httpx
from loguru import logger
from app.config import Config


SEARCH_SYSTEM_PROMPT = """你是一个TG频道消息搜索助手。用户输入关键词，你的任务：
1. 分析用户意图，理解搜索需求
2. 扩展相关关键词（最多5个同义词/相关词）
3. 提供简短的搜索建议

输出格式（JSON）：
{"main_keyword":"主关键词","related_keywords":["词1","词2","词3","词4","词5"],"search_hint":"搜索建议"}
只输出JSON，不要有其他内容。"""

CHAT_SYSTEM_PROMPT = """你是一个TG频道消息知识库问答助手。用户可以向你提问关于TG频道内容的任何问题，你会根据已有的搜索知识库帮助用户解答。"""


class AIService:
    """AI 模型调用服务（支持多 API 池 + 自动故障切换）"""

    def __init__(self):
        self.provider = "deepseek"
        self.default_api_base = "https://api.deepseek.com"
        self.default_model = "deepseek-chat"
        self.max_tokens = 1024
        self.temperature = 0.7
        self.keyword_expand = True
        self.summarize_results = True
        self.free_daily_limit = 3
        self.search_system_prompt = SEARCH_SYSTEM_PROMPT
        self.chat_system_prompt = CHAT_SYSTEM_PROMPT

        # API 池：列表，每项 {"name", "api_base", "api_key", "model", "priority", "enabled"}
        self._api_keys: List[dict] = []
        self._key_lock = threading.Lock()
        self._current_index = 0
        self._fail_count: dict = {}  # key hash -> consecutive fail count
        self._load_from_config()

    def _load_from_config(self):
        """从 Config 加载基础 AI 配置（兼容旧单 API 模式）"""
        self.provider = getattr(Config, "AI_PROVIDER", "deepseek") or "deepseek"
        self.default_api_base = getattr(Config, "AI_API_BASE", "https://api.deepseek.com") or "https://api.deepseek.com"
        self.default_model = getattr(Config, "AI_MODEL", "deepseek-chat") or "deepseek-chat"
        self.max_tokens = getattr(Config, "AI_MAX_TOKENS", 1024) or 1024
        self.temperature = getattr(Config, "AI_TEMPERATURE", 0.7) or 0.7
        self.keyword_expand = getattr(Config, "AI_KEYWORD_EXPAND", True)
        self.summarize_results = getattr(Config, "AI_SUMMARIZE_RESULTS", True)
        self.free_daily_limit = getattr(Config, "AI_FREE_DAILY_LIMIT", 3) or 3

    async def load_from_db(self):
        """从数据库加载多 API 池配置和基础设置"""
        try:
            from app.ai.settings_manager import get_ai_config
            cfg = await get_ai_config()

            # 基础配置
            if cfg.get("AI_PROVIDER"):
                self.provider = cfg["AI_PROVIDER"]
            if cfg.get("AI_API_BASE"):
                self.default_api_base = cfg["AI_API_BASE"]
            if cfg.get("AI_MODEL"):
                self.default_model = cfg["AI_MODEL"]
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

            # 多 API 池
            raw_keys = cfg.get("AI_API_KEYS", "")
            if raw_keys and isinstance(raw_keys, str):
                try:
                    self._api_keys = json.loads(raw_keys)
                except (json.JSONDecodeError, TypeError):
                    self._api_keys = []
            elif isinstance(raw_keys, list):
                self._api_keys = raw_keys

            # 兼容旧单 API Key：如果有 API_KEY 则加入池首项
            old_key = cfg.get("AI_API_KEY", "") or getattr(Config, "AI_API_KEY", "")
            if old_key and not any(k.get("api_key") == old_key for k in self._api_keys):
                self._api_keys.insert(0, {
                    "name": "默认API",
                    "api_base": self.default_api_base,
                    "api_key": old_key,
                    "model": self.default_model,
                    "priority": 1,
                    "enabled": True,
                })

            self._api_keys = [k for k in self._api_keys if k.get("enabled") and k.get("api_key")]
            self._api_keys.sort(key=lambda x: x.get("priority", 99))
            self._current_index = 0
            self._fail_count.clear()

            logger.info(f"AI配置已加载: provider={self.provider}, 模型池={len(self._api_keys)}个")
        except Exception as e:
            logger.warning(f"AI配置加载失败: {e}")

    def is_configured(self) -> bool:
        """检查是否配置了可用 API"""
        if self._api_keys:
            return True
        return bool(getattr(Config, "AI_API_KEY", "")) and bool(getattr(Config, "AI_API_BASE", ""))

    def get_pool_info(self) -> dict:
        """获取 API 池状态信息"""
        return {
            "total": len(self._api_keys),
            "active": len([k for k in self._api_keys if k.get("enabled")]),
            "keys": [
                {
                    "name": k.get("name", "未命名"),
                    "api_base": k.get("api_base", ""),
                    "model": k.get("model", ""),
                    "enabled": k.get("enabled", True),
                    "priority": k.get("priority", 99),
                    "key_preview": (k.get("api_key", "")[:8] + "****") if k.get("api_key") else "",
                }
                for k in self._api_keys
            ],
        }

    async def _call_api_with_fallback(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        调用 API，支持多密钥自动故障切换
        轮流尝试池中的每个 key，失败后跳到下一个
        """
        keys_to_try = self._api_keys[:]
        if not keys_to_try:
            # 回退到旧单 API 模式
            api_key = getattr(Config, "AI_API_KEY", "")
            api_base = getattr(Config, "AI_API_BASE", "https://api.deepseek.com")
            model = getattr(Config, "AI_MODEL", "deepseek-chat")
            if not api_key:
                return {
                    "content": "❌ AI 功能未配置，请联系管理员在后台添加 API Key",
                    "model": "", "input_tokens": 0, "output_tokens": 0, "pool_used": "",
                }
            keys_to_try = [{"name": "默认", "api_base": api_base, "api_key": api_key, "model": model}]

        last_error = ""
        for idx, key_conf in enumerate(keys_to_try):
            api_key = key_conf.get("api_key", "")
            api_base = key_conf.get("api_base", self.default_api_base)
            model = key_conf.get("model", self.default_model)
            key_name = key_conf.get("name", f"key-{idx}")

            url = f"{api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    content = choice.get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    return {
                        "content": content,
                        "model": data.get("model", model),
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                        "pool_used": key_name,
                    }
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                body = e.response.text[:200]
                last_error = f"{status}: {body}"
                logger.warning(f"AI API [{key_name}] 失败 ({status}): {last_error}")
                with self._key_lock:
                    self._fail_count[key_name] = self._fail_count.get(key_name, 0) + 1
                if status == 401 or status == 403:
                    logger.warning(f"AI API [{key_name}] 密钥无效，已标记跳过")
                    key_conf["enabled"] = False
                    try:
                        from app.ai.settings_manager import save_ai_setting
                        await save_ai_setting("AI_API_KEYS", json.dumps(self._api_keys, ensure_ascii=False))
                    except Exception:
                        pass
                continue
            except Exception as e:
                last_error = str(e)[:100]
                logger.warning(f"AI API [{key_name}] 异常: {last_error}")
                with self._key_lock:
                    self._fail_count[key_name] = self._fail_count.get(key_name, 0) + 1
                continue

        # 所有 key 都失败
        if self._api_keys:
            return {
                "content": f"❌ AI 服务暂时不可用（已尝试 {len(keys_to_try)} 个接口），请稍后重试",
                "model": "", "input_tokens": 0, "output_tokens": 0, "pool_used": "",
            }
        return {
            "content": "❌ AI 功能未配置，请联系管理员设置 API Key",
            "model": "", "input_tokens": 0, "output_tokens": 0, "pool_used": "",
        }

    async def _call_api(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """兼容旧接口，内部调用带故障切换的方法"""
        result = await self._call_api_with_fallback(messages, temperature, max_tokens)
        # 返回兼容格式（去掉 pool_used）
        return {
            "content": result["content"],
            "model": result["model"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "pool_used": result.get("pool_used", ""),
        }

    async def expand_keyword(self, keyword: str) -> dict:
        if not self.keyword_expand or not self.is_configured():
            logger.warning(f"AI扩展跳过: keyword_expand={self.keyword_expand}, is_configured={self.is_configured()}, api_keys={len(self._api_keys)}")
            return {"main_keyword": keyword, "related_keywords": [keyword], "search_hint": ""}

        messages = [
            {"role": "system", "content": self.search_system_prompt},
            {"role": "user", "content": keyword},
        ]
        logger.info(f"AI开始扩展关键词: {keyword!r}, api_keys={len(self._api_keys)}, keys={[k.get('name') for k in self._api_keys]}")
        result = await self._call_api(messages)
        content = result.get("content", "")
        pool_used = result.get("pool_used", "")
        logger.info(f"AI扩展结果: pool_used={pool_used!r}, content={content!r}")

        expanded = {"main_keyword": keyword, "related_keywords": [keyword], "search_hint": ""}
        if content.startswith("❌") or "不可用" in content or "未配置" in content:
            logger.warning(f"AI扩展失败: {content[:200]}")
            result["expanded"] = expanded
            result["tokens_used"] = 0
            return result
        # 去除markdown代码块包裹（如 ```json ... ``` 或 前导换行+代码块）
        # 使用贪婪匹配 .* 确保匹配到最后一个 ```，避免匹配到嵌套的内部代码块
        import re as _re
        clean = content.strip()
        # 匹配 ```json ... ``` 或 ``` ... ``` （贪婪模式 .* 确保匹配到最后一个 ```）
        _m = _re.search(r'```(?:json)?\s*(.*)\s*```', clean, _re.DOTALL)
        if _m:
            clean = _m.group(1).strip()
        try:
            parsed = json.loads(clean)
            expanded.update(parsed)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"AI扩展JSON解析失败: {e}, content={content[:200]!r}")
            expanded["search_hint"] = content[:100] if content else ""

        result["expanded"] = expanded
        result["tokens_used"] = result.get("input_tokens", 0) + result.get("output_tokens", 0)
        logger.info(f"AI扩展成功: expanded={json.dumps(expanded, ensure_ascii=False)}, hint={expanded.get('search_hint')!r}")
        logger.info(f"AI扩展返回keys: {list(result.keys())}")
        return result

    async def summarize_search_results(self, keyword: str, results: list) -> str:
        if not self.summarize_results or not self.is_configured():
            return ""
        if not results:
            return ""

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

    async def chat(self, user_question: str, context_results: Optional[list] = None) -> dict:
        if not self.is_configured():
            return {
                "content": "❌ AI 功能未配置，请联系管理员在后台添加 API Key",
                "input_tokens": 0, "output_tokens": 0,
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

    async def smart_search(self, keyword: str, results: list) -> dict:
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

    async def health_check(self) -> dict:
        """检测所有 API 的健康状态"""
        results = []
        for key_conf in self._api_keys:
            api_key = key_conf.get("api_key", "")
            api_base = key_conf.get("api_base", "")
            model = key_conf.get("model", "deepseek-chat")
            name = key_conf.get("name", "未命名")
            if not api_key or not api_base:
                results.append({"name": name, "status": "no_config", "elapsed_ms": 0})
                continue
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    t0 = __import__("time").perf_counter()
                    resp = await client.post(
                        f"{api_base.rstrip('/')}/chat/completions",
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                        json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                    )
                    elapsed = int((__import__("time").perf_counter() - t0) * 1000)
                    results.append({
                        "name": name, "api_base": api_base, "model": model,
                        "status": "ok" if resp.status_code == 200 else f"error_{resp.status_code}",
                        "elapsed_ms": elapsed,
                    })
            except Exception as e:
                results.append({"name": name, "status": f"error: {str(e)[:50]}", "elapsed_ms": 0})
        return {"keys": results, "healthy_count": sum(1 for r in results if r["status"] == "ok")}


ai_service = AIService()
