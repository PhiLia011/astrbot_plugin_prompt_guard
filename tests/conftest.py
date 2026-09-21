"""为插件单测准备最小 AstrBot 环境桩。

插件运行在 AstrBot 进程里，依赖 `astrbot.*`。单测只关心插件自己的逻辑，
所以这里用轻量桩替换这些模块，保证不安装 AstrBot 也能跑测试。
"""

from __future__ import annotations

import logging
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]

# 以包的形式导入插件，覆盖 `from .pg_guard import ...` 这条主路径。
if str(PLUGIN_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR.parent))


class _Config(dict):
    """AstrBotConfig 桩：就是个 dict。"""

    def save_config(self) -> None:  # pragma: no cover - 插件不调用
        return None


class _MessageChain:
    def __init__(self, chain: list[Any] | None = None) -> None:
        self.chain = list(chain or [])

    def message(self, text: str) -> _MessageChain:
        self.chain.append(text)
        return self


class _MessageEventResult:
    def __init__(self, chain: list[Any] | None = None) -> None:
        self.chain = list(chain or [])


class _AstrMessageEvent:
    """基类桩，插件只做类型标注用。"""


class _Filter:
    class PermissionType:
        ADMIN = "admin"
        MEMBER = "member"

    def on_llm_request(self, **_kwargs: Any):
        def decorator(func):
            return func

        return decorator

    def command(self, *_args: Any, **_kwargs: Any):
        def decorator(func):
            return func

        return decorator

    def permission_type(self, *_args: Any, **_kwargs: Any):
        def decorator(func):
            return func

        return decorator


@dataclass
class _ProviderRequest:
    prompt: str | None = None
    system_prompt: str = ""
    session_id: str | None = ""
    image_urls: list[str] = field(default_factory=list)
    audio_urls: list[str] = field(default_factory=list)
    extra_user_content_parts: list[Any] = field(default_factory=list)
    contexts: list[dict] = field(default_factory=list)


@dataclass
class _TextPart:
    text: str
    temp: bool = False

    def mark_as_temp(self) -> _TextPart:
        self.temp = True
        return self


class _Star:
    def __init__(self, context: Any = None) -> None:
        self.context = context


def _install_stubs() -> None:
    astrbot = types.ModuleType("astrbot")
    astrbot.__path__ = []  # type: ignore[attr-defined]

    api = types.ModuleType("astrbot.api")
    api.__path__ = []  # type: ignore[attr-defined]
    api.AstrBotConfig = _Config
    api.logger = logging.getLogger("astrbot")

    event_mod = types.ModuleType("astrbot.api.event")
    event_mod.AstrMessageEvent = _AstrMessageEvent
    event_mod.MessageChain = _MessageChain
    event_mod.MessageEventResult = _MessageEventResult
    event_mod.filter = _Filter()

    provider_mod = types.ModuleType("astrbot.api.provider")
    provider_mod.ProviderRequest = _ProviderRequest

    star_mod = types.ModuleType("astrbot.api.star")
    star_mod.Context = object
    star_mod.Star = _Star

    def register(*_args: Any, **_kwargs: Any):
        def decorator(cls):
            return cls

        return decorator

    star_mod.register = register

    core = types.ModuleType("astrbot.core")
    core.__path__ = []  # type: ignore[attr-defined]
    agent = types.ModuleType("astrbot.core.agent")
    agent.__path__ = []  # type: ignore[attr-defined]
    agent_message = types.ModuleType("astrbot.core.agent.message")
    agent_message.TextPart = _TextPart

    astrbot.api = api  # type: ignore[attr-defined]
    astrbot.core = core  # type: ignore[attr-defined]

    for name, module in {
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.event": event_mod,
        "astrbot.api.provider": provider_mod,
        "astrbot.api.star": star_mod,
        "astrbot.core": core,
        "astrbot.core.agent": agent,
        "astrbot.core.agent.message": agent_message,
    }.items():
        sys.modules[name] = module


_install_stubs()


class FakeEvent(_AstrMessageEvent):
    """AstrMessageEvent 的最小测试替身。"""

    def __init__(self, persona_name: str = "") -> None:
        self._stopped = False
        self.sent: list[Any] = []
        self.unified_msg_origin = "aiocqhttp:GroupMessage:10000"
        self._extra: dict[str, Any] = {}
        if persona_name:
            self._extra["_persona_name"] = persona_name

    def stop_event(self) -> None:
        self._stopped = True

    def is_stopped(self) -> bool:
        return self._stopped

    def get_extra(self, key: str | None = None, default: Any = None) -> Any:
        if key is None:
            return dict(self._extra)
        return self._extra.get(key, default)

    def set_extra(self, key: str, value: Any) -> None:
        self._extra[key] = value

    def plain_result(self, text: str) -> str:
        return text

    async def send(self, message: Any) -> None:
        self.sent.append(message)


class FakePersona:
    def __init__(self, name: str) -> None:
        self.name = name


class FakePersonaManager:
    def __init__(self, personas: dict[str, str] | None = None) -> None:
        self._personas = personas or {}

    def get_persona(self, persona_id: str):
        name = self._personas.get(persona_id)
        return FakePersona(name) if name else None


class FakeConversation:
    def __init__(self, persona_id: str | None = None) -> None:
        self.persona_id = persona_id


class FakeConversationManager:
    def __init__(self, persona_id: str | None = None) -> None:
        self._persona_id = persona_id

    async def get_curr_conversation_id(self, _origin: str) -> str | None:
        return "conv-1" if self._persona_id else None

    async def get_conversation(self, _origin: str, _conversation_id: str):
        return FakeConversation(self._persona_id)


@pytest.fixture
def plugin_module():
    from astrbot_plugin_prompt_guard import main as plugin_main

    return plugin_main


@pytest.fixture
def make_plugin(plugin_module):
    """按给定配置构造插件实例。"""

    def _factory(config: dict[str, Any] | None = None, context: Any = None):
        context = (
            context
            if context is not None
            else types.SimpleNamespace(
                persona_manager=FakePersonaManager(),
                conversation_manager=FakeConversationManager(),
            )
        )
        return plugin_module.PromptGuardPlugin(context, _Config(config or {}))

    return _factory


@pytest.fixture
def event():
    return FakeEvent()


@pytest.fixture
def request_cls():
    return _ProviderRequest
