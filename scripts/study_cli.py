#!/usr/bin/env python3
"""Cyberpunk Chinese chat shell for the Study Hacker harness."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.runtime import HarnessRuntime  # noqa: E402
from harness.validation import validate_task  # noqa: E402


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

VERSION = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
CONFIG_PATH = ROOT / ".study-hacker.local.json"
ENV_PATH = ROOT / ".env.local"
COLOR_ENABLED = os.environ.get("NO_COLOR", "") == "" and sys.stdout.isatty()

PROVIDER_DEFAULTS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4.1"},
    "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-20250514"},
    "custom": {"base_url": "https://api.example.com/v1", "model": "default"},
}

TRUSTED_API_HOSTS = {
    "deepseek": {"api.deepseek.com"},
    "openai": {"api.openai.com"},
    "anthropic": {"api.anthropic.com", "api.deepseek.com"},
}

RUN_WORDS = (
    "开始执行",
    "开始运行",
    "执行",
    "运行",
    "生成",
    "创建",
    "帮我做",
    "制定",
    "输出",
    "做一个",
    "run",
)

EXECUTE_PREFIXES = (
    "开始执行",
    "开始运行",
    "开始生成",
    "开始创建",
    "正式执行",
    "正式运行",
    "正式生成",
    "正式创建",
)

EXECUTE_PHRASES = (
    "请帮我生成",
    "帮我生成",
    "请帮我创建",
    "帮我创建",
    "请帮我做",
    "帮我做",
    "请输出",
    "输出一份",
    "请制定",
    "制定一份",
)

NON_EXECUTE_HINTS = (
    "不要生成",
    "先不要生成",
    "不用生成",
    "别生成",
    "不生成",
    "不要执行",
    "先不要执行",
    "不用执行",
    "别执行",
    "不执行",
    "不想执行",
    "不想开始执行",
    "暂不执行",
    "暂不开始执行",
    "不要创建",
    "先不要创建",
    "不用创建",
    "别创建",
    "不创建",
    "不要文件",
    "不要产出文件",
    "不用产出文件",
    "先别产出",
)

LOW_LEVEL_HINTS = (
    "0基础",
    "零基础",
    "完全0基础",
    "完全 0 基础",
    "小白",
    "新手",
    "入门",
    "没基础",
    "没有基础",
    "完全不懂",
    "不了解",
    "不懂",
    "只听过",
    "听过概念",
)

MID_LEVEL_HINTS = (
    "不算小白",
    "了解一点",
    "懂一点",
    "有基础",
    "做过简单调研",
    "学过",
    "用过",
    "看过资料",
)

HIGH_LEVEL_HINTS = (
    "有项目经验",
    "项目经验",
    "从业经验",
    "从业",
    "工作经验",
    "熟悉",
    "资深",
)

EXPERT_ROLE_WORDS = (
    "专家",
    "高手",
    "达人",
    "顾问",
    "分析师",
    "研究员",
    "工程师",
    "产品经理",
)

LEARNING_INTENT_WORDS = (
    "学习",
    "想学",
    "学一下",
    "了解",
    "入门",
    "掌握",
    "研究",
    "成为",
)

OUTLINE_PHASES = (
    "定位目标与基础水平",
    "一句话定义与最小词汇",
    "领域地图与关键关系",
    "领域内小案例练习",
    "真实任务拆解",
    "交付物与复盘",
)


class Neon:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    CYAN = "\033[38;5;51m"
    PINK = "\033[38;5;201m"
    VIOLET = "\033[38;5;141m"
    YELLOW = "\033[38;5;220m"
    ORANGE = "\033[38;5;208m"
    GREEN = "\033[38;5;82m"
    RED = "\033[38;5;196m"
    GREY = "\033[38;5;245m"


ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def enable_windows_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        return


def paint(text: str, color: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{color}{text}{Neon.RESET}"


def display_width(text: str) -> int:
    clean = ANSI_RE.sub("", text)
    width = 0
    for char in clean:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def term_width(default: int = 96) -> int:
    return max(72, min(shutil.get_terminal_size((default, 24)).columns, 180))


def wrap_row(row: str, width: int) -> list[str]:
    clean = ANSI_RE.sub("", row)
    if not clean:
        return [""]
    lines: list[str] = []
    current = ""
    used = 0
    for char in clean:
        if char == "\n":
            lines.append(current)
            current = ""
            used = 0
            continue
        char_width = 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        if used and used + char_width > width:
            lines.append(current.rstrip())
            current = ""
            used = 0
        current += char
        used += char_width
    if current or not lines:
        lines.append(current.rstrip())
    return lines


def panel(title: str, rows: list[str], color: str = Neon.CYAN) -> None:
    width = term_width()
    inner = width - 4
    top = "+" + "-" * (width - 2) + "+"
    print(paint(top, color))
    label = f" {title} "
    print(
        paint("| ", color)
        + paint(label, Neon.BOLD + Neon.YELLOW)
        + " " * max(inner - display_width(label), 0)
        + paint(" |", color)
    )
    print(paint("|" + "-" * (width - 2) + "|", color))
    for row in rows:
        for wrapped in wrap_row(row, inner):
            print(paint("| ", color) + wrapped + " " * max(inner - display_width(wrapped), 0) + paint(" |", color))
    print(paint(top, color))


def show_thinking() -> None:
    if not sys.stdout.isatty():
        return
    print(paint("… 正在思考", Neon.GREY), end="\r", flush=True)


def clear_thinking() -> None:
    if not sys.stdout.isatty():
        return
    print(" " * min(term_width(), 100), end="\r", flush=True)


def banner() -> None:
    art = [
        "  ____ _____ _   _ ____  __   __      _   _    _    ____ _  _______ ____  ",
        " / ___|_   _| | | |  _ \\ \\ \\ / /_____| | | |  / \\  / ___| |/ / ____|  _ \\ ",
        " \\___ \\ | | | | | | | | | \\ V /______| |_| | / _ \\| |   | ' /|  _| | |_) |",
        "  ___) || | | |_| | |_| |  | |       |  _  |/ ___ \\ |___| . \\| |___|  _ < ",
        " |____/ |_|  \\___/|____/   |_|       |_| |_/_/   \\_\\____|_|\\_\\_____|_| \\_\\",
    ]
    print()
    for idx, line in enumerate(art):
        color = Neon.CYAN if idx < 2 else Neon.PINK if idx < 4 else Neon.ORANGE
        print(paint(line, color))
    print(paint("        STUDY-HACKER // 专家速成 Agent 终端", Neon.BOLD + Neon.YELLOW))
    print(paint(f"        v{VERSION}  直接对话 | CLI harness | RAG | queue | approval gate", Neon.GREY))
    print(paint("=" * term_width(), Neon.PINK))


def boot_sequence() -> None:
    if not sys.stdout.isatty():
        return
    for item in ["加载对话核心", "挂载 harness 工具", "同步风险闸门", "预热 RAG 索引器", "启动审批电路"]:
        print(paint("[BOOT] ", Neon.PINK) + paint(item, Neon.GREY))
        time.sleep(0.035)


def is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def api_base_host(base_url: str) -> str:
    return urllib.parse.urlparse(base_url).hostname or ""


def api_base_is_trusted(provider: str, base_url: str) -> bool:
    host = api_base_host(base_url).lower()
    if not host:
        return False
    trusted_hosts = TRUSTED_API_HOSTS.get(provider.lower(), set())
    return host in trusted_hosts


def api_key_send_allowed(config: dict[str, Any]) -> bool:
    provider = str(config.get("provider", "")).lower()
    base_url = str(config.get("base_url") or os.environ.get("STUDY_HACKER_BASE_URL", ""))
    return api_base_is_trusted(provider, base_url) or bool(config.get("allow_untrusted_base_url"))


def confirm_untrusted_api_base(provider: str, base_url: str) -> bool:
    if api_base_is_trusted(provider, base_url):
        return True
    host = api_base_host(base_url) or base_url
    panel(
        "API 安全确认",
        [
            f"provider={provider} 的 base URL 不是内置可信域名：{host}",
            "继续后，你的 API key 会被发送到这个域名。",
            "如果这是你自己的代理网关，请输入 YES 确认；否则请重新配置。",
        ],
        Neon.RED,
    )
    return prompt("确认发送 API key 到该域名，输入 YES", "") == "YES"


def safe_config_value(value: Any) -> str:
    text = str(value or "n/a")
    lowered = text.lower()
    if lowered.startswith(("sk-", "sk_", "sk-proj")) or len(text) > 64:
        return "已隐藏"
    return text


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_file(values: dict[str, str]) -> None:
    lines = [
        "# Study Hacker local API config. Do not commit this file.",
        f"STUDY_HACKER_PROVIDER={values['provider']}",
        f"STUDY_HACKER_BASE_URL={values['base_url']}",
        f"STUDY_HACKER_MODEL={values['model']}",
        f"STUDY_HACKER_API_KEY={values['api_key']}",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def load_api_config() -> dict[str, Any]:
    env_values = read_env_file(ENV_PATH)
    for key, value in env_values.items():
        os.environ.setdefault(key, value)

    config = read_json_if_exists(CONFIG_PATH)
    if not config and os.environ.get("STUDY_HACKER_API_KEY"):
        provider = os.environ.get("STUDY_HACKER_PROVIDER", "custom")
        config = {
            "configured": True,
            "provider": provider,
            "base_url": os.environ.get("STUDY_HACKER_BASE_URL", provider_defaults(provider)["base_url"]),
            "model": os.environ.get("STUDY_HACKER_MODEL", provider_defaults(provider)["model"]),
            "api_key_env": "STUDY_HACKER_API_KEY",
        }
    return config


def provider_defaults(provider: str) -> dict[str, str]:
    return PROVIDER_DEFAULTS.get(provider.lower(), PROVIDER_DEFAULTS["custom"])


def api_is_configured() -> bool:
    config = load_api_config()
    key_env = str(config.get("api_key_env", "STUDY_HACKER_API_KEY"))
    base_url = str(config.get("base_url") or os.environ.get("STUDY_HACKER_BASE_URL", ""))
    model = str(config.get("model") or os.environ.get("STUDY_HACKER_MODEL", ""))
    return bool(config.get("configured") and os.environ.get(key_env) and is_http_url(base_url) and model)


def prompt(label: str, default: str = "") -> str:
    suffix = paint(f" [{default}]", Neon.GREY) if default else ""
    value = input(paint(f">> {label}", Neon.CYAN) + suffix + paint(" :: ", Neon.PINK)).strip()
    return value or default


def configure_api(force: bool = False) -> None:
    if not force and api_is_configured():
        return
    if not sys.stdin.isatty() or os.environ.get("STUDY_HACKER_SKIP_CONFIG") == "1":
        return

    panel(
        "首次 API 配置",
        [
            "只需要配置一次 provider、base URL、model 和 API key，之后启动不会再弹出。",
            "密钥只写入本地 .env.local；运行信息写入 .study-hacker.local.json。",
            "如果暂时只想用本地 harness，可按 Ctrl+C 退出后设置 STUDY_HACKER_SKIP_CONFIG=1。",
        ],
        Neon.ORANGE,
    )
    while True:
        provider = prompt("provider: deepseek / openai / anthropic / custom", "deepseek").lower()
        defaults = provider_defaults(provider)
        base_url = prompt("API base URL", defaults["base_url"])
        model = prompt("model", defaults["model"])
        allow_untrusted_base_url = False
        if not confirm_untrusted_api_base(provider, base_url):
            continue
        if not api_base_is_trusted(provider, base_url):
            allow_untrusted_base_url = True
        api_key = getpass.getpass(paint(">> API key（隐藏输入）:: ", Neon.CYAN)).strip()
        if not api_key:
            panel("需要 API key", ["请输入 API key 完成配置，或按 Ctrl+C 退出。"], Neon.RED)
            continue

        write_env_file({"provider": provider, "base_url": base_url, "model": model, "api_key": api_key})
        os.environ["STUDY_HACKER_PROVIDER"] = provider
        os.environ["STUDY_HACKER_BASE_URL"] = base_url
        os.environ["STUDY_HACKER_MODEL"] = model
        os.environ["STUDY_HACKER_API_KEY"] = api_key
        CONFIG_PATH.write_text(
            json.dumps(
                {
                    "configured": True,
                    "provider": provider,
                    "base_url": base_url,
                    "model": model,
                    "api_key_env": "STUDY_HACKER_API_KEY",
                    "allow_untrusted_base_url": allow_untrusted_base_url,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        panel("API 配置已保存", [f"provider    {provider}", f"model       {model}", "secret      已保存到 .env.local"], Neon.GREEN)
        return


def dashboard() -> None:
    config = load_api_config()
    api_status = "已配置" if api_is_configured() else "未配置"
    if api_is_configured():
        provider = safe_config_value(config.get("provider", "n/a"))
        model = safe_config_value(config.get("model", "n/a"))
    else:
        provider = "等待首次配置"
        model = "n/a"
    panel(
        "系统在线",
        [
            paint("模式", Neon.YELLOW) + "        直接对话，不再进入问卷式引导",
            paint("能力", Neon.YELLOW) + "        聊天、解释、拆解目标、检查状态、按需调用 harness 执行",
            paint("执行", Neon.YELLOW) + "        说“开始执行：目标”或使用 /run <目标>",
            paint("API", Neon.YELLOW) + f"         {api_status} | {provider} | {model}",
        ],
        Neon.CYAN,
    )
    panel(
        "命令",
        [
            paint("/run <目标>", Neon.GREEN) + "  调用 harness 生成专家速成包",
            paint("/status", Neon.GREEN) + "    查看最近一次执行状态",
            paint("/open", Neon.GREEN) + "      显示最近报告路径",
            paint("/config", Neon.GREEN) + "    重新配置 API",
            paint("/help", Neon.GREEN) + "      查看帮助",
            paint("/exit", Neon.GREEN) + "      退出",
        ],
        Neon.PINK,
    )


def help_text() -> None:
    panel(
        "帮助",
        [
            "你可以像聊天一样直接输入：你好、检查联网状态、我想了解 AI 创业。",
            "当你说“我想成为某领域专家”时，我会先确认了解程度，再决定从基础解释还是实战任务开始。",
            "需要真正产出文件时，说：开始执行：我想用一周研究 AI 应用创业。",
            "也可以使用命令：/run 我想用一周研究 AI 应用创业。",
            "默认执行参数：未说明基础时按 0基础 保守处理、每天1小时、中国/全球、最近4个月、离线安全模式。",
            "如果要联网检索，在目标里写“允许联网”或“检索最新资料/GitHub”。",
        ],
        Neon.VIOLET,
    )


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def infer_user_level(text: str) -> str:
    compact = compact_text(text)
    lowered = text.lower()
    if any(hint.lower() in lowered or compact_text(hint) in compact for hint in HIGH_LEVEL_HINTS):
        return "有相关项目经验"
    if any(hint.lower() in lowered or compact_text(hint) in compact for hint in MID_LEVEL_HINTS):
        return "做过简单调研"
    if any(hint.lower() in lowered or compact_text(hint) in compact for hint in LOW_LEVEL_HINTS):
        return "0基础"
    return ""


def is_low_user_level(level: str) -> bool:
    compact = compact_text(level)
    low_markers = ("0基础", "零基础", "小白", "新手", "入门", "没基础", "没有基础", "完全不懂", "不了解", "不懂", "听过概念")
    return any(compact_text(hint) in compact for hint in low_markers)


def is_expert_aspiration(text: str) -> bool:
    compact = compact_text(text)
    has_role = any(role in text for role in EXPERT_ROLE_WORDS)
    has_intent = any(word in compact for word in ["想成为", "想要成为", "希望成为", "我要成为", "成长为", "成为"])
    return has_role and has_intent


def extract_expert_subject(text: str) -> str:
    patterns = [
        r"(?:想要|希望|想|我要|准备|打算).{0,8}(?:成为|成长为|变成|做)(?:一名|一个)?(?P<subject>[^，。！？,.!?]{1,40}?)(?:专家|高手|达人|顾问|分析师|研究员|工程师|产品经理)",
        r"(?:成为|成长为|变成)(?:一名|一个)?(?P<subject>[^，。！？,.!?]{1,40}?)(?:专家|高手|达人|顾问|分析师|研究员|工程师|产品经理)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            subject = match.group("subject").strip(" 的")
            subject = re.sub(r"^(某个|某方面|一个|一名)", "", subject).strip(" 的")
            if subject:
                return subject
    return infer_domain(text)


def subject_from_text(text: str) -> str:
    if is_expert_aspiration(text):
        return extract_expert_subject(text)
    if any(word in text for word in ["Harness Engineering", "harness engineering", "openclaw", "OpenClaw", "AI 代理", "AI Agent", "agent 工具", "Agent 工具", "智能体"]):
        return "AI Agent 工程 / Harness Engineering"
    if any(word in text for word in ["萃取时间", "冲煮变量", "粉水比", "水温", "手冲", "法压", "压豆壶", "咖啡粉", "咖啡"]):
        if "萃取时间" in text:
            return "咖啡萃取时间"
        if "冲煮变量" in text:
            return "咖啡冲煮变量"
        return "咖啡冲煮"
    if any(word in text for word in ["简历", "投递", "产品岗位", "产品岗", "求职", "面试"]):
        if "AI" in text or "ChatGPT" in text:
            return "AI 优化简历与产品岗求职"
        return "简历优化与求职"
    for pattern in (
        r"(?:想要|希望|想|我要|准备|打算)?(?:学习|想学|学一下|了解|入门|掌握|研究)(?P<subject>[^，。！？,.!?]{2,40})",
        r"(?:想用|希望用|我要用)(?P<subject>AI[^，。！？,.!?]{2,40})",
    ):
        match = re.search(pattern, text)
        if match:
            subject = match.group("subject").strip(" ：:的")
            subject = re.sub(r"^(一下|一下子|怎么|如何|系统|系统性)", "", subject).strip(" ：:的")
            if subject and subject not in {"这个", "这个领域", "系统学"}:
                return subject
    if "AI" in text and "产品" in text:
        return "AI 产品学习"
    if "产品" in text:
        return "产品开发"
    return ""


def history_asked_user_level(history: list[dict[str, str]]) -> bool:
    for item in reversed(history[-4:]):
        if item.get("role") != "assistant":
            continue
        content = item.get("content", "")
        if ("了解程度" in content or "基础" in content) and ("哪档" in content or "哪一种" in content or "确认" in content):
            return True
    return False


def subject_from_history(history: list[dict[str, str]]) -> str:
    for item in reversed(history[-6:]):
        content = item.get("content", "")
        match = re.search(r"「([^」]{1,40})」", content)
        if match and match.group(1) not in {"某方面", "这个领域", "系统学"}:
            return match.group(1)
        subject = subject_from_text(content)
        if subject:
            return subject
    joined = " ".join(item.get("content", "") for item in history[-8:])
    if any(word in joined for word in ["萃取时间", "冲煮变量", "粉水比", "水温", "手冲", "法压", "压豆壶", "咖啡粉", "咖啡"]):
        if "萃取时间" in joined:
            return "咖啡萃取时间"
        if "冲煮变量" in joined:
            return "咖啡冲煮变量"
        return "咖啡冲煮"
    if any(word in joined for word in ["简历", "投递", "产品岗位", "产品岗", "求职", "面试"]):
        if "AI" in joined or "ChatGPT" in joined:
            return "AI 优化简历与产品岗求职"
        return "简历优化与求职"
    if "AI" in joined and "产品" in joined:
        return "AI 产品学习"
    if "产品" in joined:
        return "产品开发"
    return "这个领域"


def conversation_user_level(history: list[dict[str, str]], current_text: str = "") -> str:
    current = infer_user_level(current_text)
    if current:
        return current
    for item in reversed(history[-12:]):
        if item.get("role") != "user":
            continue
        level = infer_user_level(item.get("content", ""))
        if level:
            return level
    return ""


def infer_learning_purpose(text: str) -> str:
    if any(word in text for word in ["创业", "商业化", "商业模式", "做公司", "客户验证", "融资"]):
        return "创业"
    if any(word in text for word in ["求职", "找工作", "面试", "简历", "投递", "跳槽"]):
        return "求职"
    if any(word in text for word in ["做项目", "项目作品", "作品集", "个人项目", "实战项目"]):
        return "做项目"
    if any(word in text for word in ["研究", "调研", "行业分析", "投资研究"]):
        return "研究"
    if any(word in text for word in ["咨询", "交付", "客户方案"]):
        return "咨询交付"
    return ""


def infer_daily_time(text: str) -> str:
    if any(word in text for word in ["全职", "全天", "full-time", "full time"]):
        return "全职投入"
    if "半小时" in text:
        return "30分钟"
    match = re.search(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>小时|h|hour|分钟|分|min)", text, re.I)
    if not match:
        return ""
    number = match.group("num")
    unit = match.group("unit").lower()
    if unit in {"h", "hour"}:
        return f"{number}小时"
    if unit in {"分", "min"}:
        return f"{number}分钟"
    return f"{number}{match.group('unit')}"


def conversation_learning_context(history: list[dict[str, str]], current_text: str = "") -> dict[str, str]:
    purpose = infer_learning_purpose(current_text)
    daily_time = infer_daily_time(current_text)
    for item in reversed(history[-12:]):
        if item.get("role") != "user":
            continue
        content = item.get("content", "")
        purpose = purpose or infer_learning_purpose(content)
        daily_time = daily_time or infer_daily_time(content)
        if purpose and daily_time:
            break
    return {"purpose": purpose, "daily_time": daily_time}


def merge_learning_context(old: dict[str, str] | None, new: dict[str, str]) -> dict[str, str]:
    old = old or {}
    return {
        "purpose": new.get("purpose") or old.get("purpose", ""),
        "daily_time": new.get("daily_time") or old.get("daily_time", ""),
    }


def outline_terms_for_subject(subject: str) -> list[str]:
    if any(word in subject for word in ["Agent", "agent", "代理", "智能体", "Harness", "harness"]):
        return ["目标", "工具", "检查", "上下文", "权限", "任务循环"]
    if any(word in subject for word in ["咖啡", "萃取", "冲煮", "粉水比", "水温"]):
        return ["咖啡粉", "热水", "时间", "水温", "粉水比", "研磨粗细"]
    if any(word in subject for word in ["简历", "求职", "岗位"]):
        return ["岗位", "经历", "匹配", "JD", "结果", "投递版本"]
    if "产品" in subject:
        return ["用户", "问题", "办法", "原型", "验证", "迭代"]
    if any(word in subject for word in ["投资", "股票", "基金"]):
        return ["标的", "行业", "财务", "估值", "风险", "证据"]
    return ["问题", "对象", "方法", "证据", "练习", "交付物"]


def outline_phase_details(subject: str, terms: list[str]) -> list[tuple[str, str]]:
    if any(word in subject for word in ["咖啡", "萃取", "冲煮", "粉水比", "水温"]):
        return [
            ("确认用户用什么器具、喝到的味道问题、基础水平和每天练习时间。", "用户能说清器具、目标味道和最困惑的一个点。"),
            (f"用一句话定义「{subject}」，只讲 3 个最小词：{', '.join(terms[:3])}。", "用户能解释热水和咖啡粉接触多久会影响味道。"),
            ("建立咖啡最小地图：水温、粉水比、研磨粗细、时间和味道之间的关系。", "用户能说出太酸/太苦时优先检查哪个变量。"),
            ("做 1 次小实验：只改一个变量，记录味道变化。", "用户能写下变量、结果和下一杯怎么调。"),
            ("设计一套自己的入门冲煮参数和调整规则。", "用户能按规则冲一杯并说明为什么这样调。"),
            ("复盘口味、参数和误区，形成下一轮练习清单。", "用户能说出最稳定的一组参数和下一次要验证的问题。"),
        ]
    if any(word in subject for word in ["简历", "求职", "岗位"]):
        return [
            ("确认简历现状、目标岗位、经验背景和投递期限。", "用户能说清是否有简历草稿、目标岗位和最大短板。"),
            (f"用一句话定义「{subject}」，只讲 3 个最小词：{', '.join(terms[:3])}。", "用户能说出岗位、经历、匹配之间的关系。"),
            ("建立求职最小地图：JD、经历、关键词、成果、投递版本。", "用户能从一个 JD 中找出 3 个关键词。"),
            ("用 1 段经历做 AI 改写练习，并人工检查夸大和失真。", "用户能把一段经历改成岗位匹配表达。"),
            ("生成一版目标岗位简历优化流程和投递清单。", "用户能形成一版可投递的简历改写方案。"),
            ("复盘简历风险、证据缺口和下一轮投递策略。", "用户能说出还要补哪段经历或哪个项目。"),
        ]
    if "产品" in subject:
        return [
            ("确认用户想做求职、项目、创业还是研究，以及是否有产品背景。", "用户能说清学习用途和目标交付物。"),
            (f"用一句话定义「{subject}」，只讲 3 个最小词：{', '.join(terms[:3])}。", "用户能用生活例子解释用户、问题、办法。"),
            ("建立产品最小地图：用户、场景、痛点、方案、验证、迭代。", "用户能拆出一个 App 功能背后的用户和问题。"),
            ("做 1 个小功能拆解练习。", "用户能写出一个功能的用户、问题、办法和验证方式。"),
            ("把练习转成 PRD 草案、求职项目或创业假设。", "用户能产出第一版产品交付物。"),
            ("复盘需求质量、证据缺口和下一轮验证。", "用户能指出自己的假设和待验证点。"),
        ]
    return [
        ("确认用户基础、用途、每天可投入时间和第一个验收目标。", "用户能说清楚自己为什么学、已有基础和时间约束。"),
        (f"用一句话定义「{subject}」，只讲 3 个最小词：{', '.join(terms[:3])}。", "用户能用自己的话复述一句话定义，并指出一个不懂的词。"),
        (f"建立「{subject}」的最小地图：角色、对象、关键变量、常见误区。", "用户能说出 3 个关键对象之间的关系。"),
        ("用领域内的小例子练一遍，不换到无关领域。", "用户能完成一个 5 分钟小练习，并知道哪里做错。"),
        ("把学习内容转成一个真实任务，拆成可执行步骤。", "用户能按步骤完成第一版业务/学习交付物。"),
        ("检查交付物、补缺口、决定下一轮学习路径。", "用户能说出自己会了什么、还卡在哪里、下一步做什么。"),
    ]


def build_learning_outline(subject: str, user_level: str = "", goal: str = "") -> dict[str, Any]:
    level = user_level or "待确认"
    terms = outline_terms_for_subject(subject)
    details = outline_phase_details(subject, terms)
    return {
        "subject": subject,
        "user_level": level,
        "goal": goal or "完成系统型入门并能做一个小练习",
        "current_phase": 0,
        "terms": terms,
        "context": {"purpose": "", "daily_time": ""},
        "phases": [
            {"name": OUTLINE_PHASES[index], "purpose": purpose, "pass_check": pass_check}
            for index, (purpose, pass_check) in enumerate(details)
        ],
    }


def infer_learning_subject(text: str, history: list[dict[str, str]]) -> str:
    subject = subject_from_text(text)
    if subject:
        return subject
    if any(word in text for word in LEARNING_INTENT_WORDS):
        subject = subject_from_history(history)
        if subject != "这个领域":
            return subject
    return ""


def ensure_learning_state(
    learning_state: dict[str, Any] | None,
    text: str,
    history: list[dict[str, str]],
) -> dict[str, Any] | None:
    direct_subject = subject_from_text(text)
    subject = infer_learning_subject(text, history)
    level = conversation_user_level(history, text)
    context = conversation_learning_context(history, text)
    if learning_state:
        if direct_subject and direct_subject != learning_state.get("subject"):
            new_state = build_learning_outline(direct_subject, level, text)
            return {**new_state, "context": merge_learning_context(new_state.get("context"), context)}
        if level and level != learning_state.get("user_level"):
            learning_state = {**learning_state, "user_level": level}
        learning_state = {**learning_state, "context": merge_learning_context(learning_state.get("context"), context)}
        if subject and subject != learning_state.get("subject") and learning_state.get("subject") == "这个领域":
            new_state = build_learning_outline(subject, level, text)
            return {**new_state, "context": merge_learning_context(new_state.get("context"), context)}
        return learning_state
    if subject:
        new_state = build_learning_outline(subject, level, text)
        return {**new_state, "context": merge_learning_context(new_state.get("context"), context)}
    return None


def advance_learning_state(learning_state: dict[str, Any] | None, user_text: str) -> dict[str, Any] | None:
    if not learning_state:
        return None
    phase = int(learning_state.get("current_phase", 0))
    if wants_childlike_explanation(user_text) or any(word in user_text for word in ["不懂", "不会", "不知道", "卡住"]):
        phase = min(phase, 1)
    elif any(word in user_text for word in ["我会了", "懂了", "明白了", "已经明白", "完成了", "做完了", "已完成"]):
        phase = min(phase + 1, len(learning_state.get("phases", [])) - 1)
    return {**learning_state, "current_phase": phase}


def learning_outline_prompt(learning_state: dict[str, Any] | None) -> str:
    if not learning_state:
        return ""
    phases = learning_state.get("phases", [])
    current_phase = int(learning_state.get("current_phase", 0))
    current = phases[current_phase] if phases else {}
    context = learning_state.get("context", {})
    phase_lines = []
    for index, phase in enumerate(phases, start=1):
        phase_lines.append(f"{index}. {phase.get('name')}: {phase.get('purpose')}")
    return (
        "\n内部学习引导大纲，仅供你自己使用，不要一次性完整展示给用户。"
        f"\n学习主题：{learning_state.get('subject')}"
        f"\n用户基础：{learning_state.get('user_level')}"
        f"\n已知用途：{context.get('purpose') or '待确认'}"
        f"\n已知每日时间：{context.get('daily_time') or '待确认'}"
        f"\n目标：{learning_state.get('goal')}"
        f"\n当前阶段：{current_phase + 1}. {current.get('name')}；目的：{current.get('purpose')}；通过标准：{current.get('pass_check')}"
        "\n完整阶段：\n" + "\n".join(phase_lines) +
        "\n推进规则：每次只推进当前阶段；用户未通过当前阶段，不要跳到后续阶段；小学生模式必须使用当前主题里的例子。"
        "不要重复询问已知用途、每日时间、基础水平或学习主题；信息足够时必须直接制定当前阶段计划并推进。"
        "只有缺少会阻塞下一步的关键资料时才反问，而且最多问 1 个问题；不需要每个回答都反问。"
    )


def history_is_beginner_mode(history: list[dict[str, str]]) -> bool:
    for item in reversed(history[-8:]):
        content = item.get("content", "")
        if infer_user_level(content) == "0基础":
            return True
        if any(marker in content for marker in ["不会一上来安排复杂任务", "3 个最小词", "像讲给小学生"]):
            return True
    return False


def wants_childlike_explanation(text: str) -> bool:
    return any(word in text for word in ["听不懂", "看不懂", "还是不懂", "更简单", "小学生", "小白话", "人话", "打比方"])


def mentions_job_or_time(text: str) -> bool:
    return any(word in text for word in ["求职", "找工作", "面试", "简历", "岗位", "每天", "30分钟", "30 分钟", "半小时"])


def simple_subject_definition(subject: str) -> str:
    if any(word in subject for word in ["咖啡", "萃取", "冲煮"]):
        return f"{subject}可以先理解成“让热水用合适的时间，把咖啡粉里的味道带出来”。"
    if any(word in subject for word in ["简历", "求职", "岗位"]):
        return f"{subject}可以先理解成“把你的经历，说成目标岗位能看懂、愿意相信的证据”。"
    if any(word in subject for word in ["Agent", "agent", "代理", "智能体", "Harness", "harness"]):
        return f"{subject}可以先理解成“让 AI 带着目标、工具和检查标准，一步步把任务做完”。"
    if "产品" in subject:
        return f"{subject}可以先理解成“发现一个真实问题，做一个办法，再验证有没有用”。"
    return f"{subject}可以先理解成“先看见一个问题，再用方法和证据把它解决到可检查”。"


def learning_plan_reply(subject: str, level: str, context: dict[str, str] | None = None) -> str:
    context = context or {}
    purpose = context.get("purpose") or "通用实战"
    daily_time = context.get("daily_time") or "1小时"
    terms = "、".join(outline_terms_for_subject(subject)[:3])
    return (
        "信息够了，我不再继续问同样的问题，先给你推进版学习计划。\n"
        f"已知：方向「{subject}」；目的：{purpose}；基础：{level or '0基础'}；每天投入：{daily_time}。\n\n"
        "我会按 5-12 天弹性推进，先走低门槛路线，觉得太浅再加速：\n"
        "第 1 关：一句话定义，只抓 3 个最小词。\n"
        "第 2 关：画最小地图，知道这个领域有哪些角色、工具、输入和输出。\n"
        "第 3 关：拆 1 个真实案例，看它怎么从目标变成任务。\n"
        "第 4 关：做 1 个小练习，产出能被检查的东西。\n"
        "第 5 关：复盘缺口，再决定要不要调用 /run 生成完整专家速成包。\n\n"
        f"现在开始第 1 关：{simple_subject_definition(subject)}\n"
        f"先记 3 个词：{terms}。今天先不用背术语，也不用直接做复杂系统。"
    )


def missing_learning_slot_question(context: dict[str, str], level: str) -> str:
    if not level or level == "待确认":
        return "为了避免难度放错，我只确认一个信息：你现在是 0基础、听过概念、做过简单调研，还是有项目经验？"
    if not context.get("purpose"):
        return "为了把练习贴近真实场景，我只确认一个信息：你学它主要是为了求职、创业、做项目、研究，还是咨询交付？"
    if not context.get("daily_time"):
        return "为了安排节奏，我只确认一个信息：你每天大概能投入 30 分钟、1 小时、2 小时，还是更多？"
    return ""


def beginner_foundation_reply(subject: str, level: str, context: dict[str, str] | None = None) -> str:
    context = context or {}
    if context.get("purpose") and context.get("daily_time"):
        return learning_plan_reply(subject, level, context)
    question = missing_learning_slot_question(context, level)
    return (
        f"收到，你现在更接近“{level}”。我会先从「{subject}」的地基讲起，不会一上来安排复杂任务。\n"
        f"先给一句话定义：{subject}就是把一个想法，变成别人真的能用、愿意用的东西或方法。\n"
        f"再用一个通俗比喻：学「{subject}」像第一次进入一座新城市，先不急着开公司或做判断，"
        "先认识地图、路标、常见角色和危险路口。\n"
        "第一轮只做三件轻任务：1. 记住这句定义；2. 只学 3 个最小词：问题、办法、试试；"
        "3. 找 1 个生活例子，比如奶茶店、外卖 App 或课程表。\n"
        + (question if question else "这一步可以直接开始，不需要再补充信息。")
    )


def experienced_foundation_reply(subject: str, level: str) -> str:
    if any(word in subject for word in ["简历", "求职", "岗位"]):
        return (
            f"明白，你是“{level}”，而且目标是「{subject}」。我不会把你拉回纯小白概念课。\n"
            "接下来更适合按这条线走：简历现状 -> 目标岗位 -> AI 改写 -> 人工检查 -> 投递版本。\n"
            "我先只确认两个关键点：你现在有简历草稿吗？目标是 C 端产品、B 端/SaaS 产品，还是 AI 产品？"
        )
    return (
        f"明白，你对「{subject}」已经是“{level}”。我会跳过纯小白解释，先帮你补框架、找盲点，再推进实战交付。\n"
        "下一步我会先确认 3 件事：目标业务场景、你已经掌握的部分、你最想补齐的薄弱点。"
        "你希望最终产出研究报告、创业验证、求职项目、咨询交付物，还是产品方案？"
    )


def expert_intake_reply(text: str, history: list[dict[str, str]] | None = None) -> str | None:
    history = history or []
    level = infer_user_level(text)
    context = conversation_learning_context(history, text)
    if is_expert_aspiration(text):
        subject = extract_expert_subject(text)
        if not level:
            return (
                f"可以，我先不急着给你排硬任务。要把你带到「{subject}」可参与业务的水平，"
                "我需要先确认你的了解程度。\n"
                "你目前是哪档：完全 0 基础 / 听过概念 / 做过简单调研 / 有项目或从业经验？"
                "你学它是为了找工作、做项目、创业，还是做研究？"
            )
        if is_low_user_level(level):
            return beginner_foundation_reply(subject, level, context)
        if context.get("purpose") and context.get("daily_time"):
            return learning_plan_reply(subject, level, context)
        return experienced_foundation_reply(subject, level)
    if level and history_asked_user_level(history):
        subject = subject_from_history(history)
        if is_low_user_level(level):
            return beginner_foundation_reply(subject, level, context)
        if context.get("purpose") and context.get("daily_time"):
            return learning_plan_reply(subject, level, context)
        return experienced_foundation_reply(subject, level)
    return None


def beginner_job_reply(subject: str) -> str:
    return (
        "可以，我们先不选复杂岗位，也不背一堆词。\n"
        f"你只需要先记住一句话：{subject}就是“发现一个问题，想一个办法，试试看有没有用”。\n"
        "每天 30 分钟先这样做：\n"
        "1. 10 分钟：打开一个你天天用的 App，比如微信、外卖或小红书。\n"
        "2. 10 分钟：写一句话：它帮谁解决了什么麻烦。\n"
        "3. 10 分钟：写一句话：如果让我改一点点，我想改哪里。\n"
        "今天不要学新术语，也不要投简历。先把“问题、办法、试试”这 3 个词搞懂。\n"
        "我先追问你：你更喜欢和人聊天沟通、写代码做东西，还是看数据做表格？不确定就直接说“不知道”。"
    )


def childlike_explanation_reply(subject: str) -> str:
    if any(word in subject for word in ["咖啡", "萃取", "冲煮", "粉水比", "水温"]):
        return (
            "好，我用小学生也能懂的说法讲，而且只用咖啡自己的例子，不跳到别的领域。\n"
            "把咖啡粉想成一包“藏着味道的小颗粒”，热水像一只小手，把味道从咖啡粉里带出来。\n"
            "萃取时间就是：热水和咖啡粉待在一起多久。\n"
            "这里面只有 3 个词：\n"
            "1. 咖啡粉：味道藏在里面。\n"
            "2. 热水：负责把味道带出来。\n"
            "3. 时间：水和咖啡粉接触多久。\n"
            "如果时间太短，就像茶包只在水里碰一下，味道会淡、可能偏酸；如果时间太长，就像茶包泡太久，可能会苦。\n"
            "所以小学生版的一句话是：咖啡萃取就是“让热水用合适的时间，把咖啡粉里的好味道带出来”。\n"
            "你现在只要回答一个问题：你用的是手冲、法压、摩卡壶、意式咖啡机，还是挂耳/速溶？"
        )
    if any(word in subject for word in ["简历", "求职", "岗位"]):
        return (
            "好，我用小学生也能懂的说法讲，而且只用求职自己的例子，不换到别的领域。\n"
            "简历就像一张“给面试官看的自我介绍卡”。AI 优化简历，就是让这张卡更容易被看懂、更像目标岗位需要的人。\n"
            "这里面只有 3 个词：\n"
            "1. 岗位：公司想找什么人。\n"
            "2. 经历：你做过什么事。\n"
            "3. 匹配：把你的经历说成岗位听得懂的话。\n"
            "小学生版一句话：AI 优化简历就是“帮你把做过的事，说成公司想看的样子”。\n"
            "你现在只要回答一句话：你要投的岗位名字是什么？"
        )
    if any(word in subject for word in ["产品"]):
        return (
            "好，我用小学生也能懂的说法讲，而且只用产品自己的例子，不换到别的领域。\n"
            "产品开发就像你想做一个“提醒同学带作业本”的小工具：先发现大家总忘带，再想办法提醒，最后试试看有没有用。\n"
            "这里面只有 3 个词：\n"
            "1. 问题：大家忘带作业本。\n"
            "2. 办法：做一个提醒小纸条，或者让手机每天提醒。\n"
            "3. 试试：先给 3 个同学用一天，看他们还会不会忘。\n"
            "这就是最小版的产品开发：发现问题，想办法，试试看。\n"
            "你现在只要回答一句话：你生活里最想解决的一个小麻烦是什么？"
        )
    return (
        f"好，我换成小学生也能懂的说法。\n"
        f"我会尽量贴着「{subject}」讲：先找一个这个领域里的小问题，再想一个小办法，最后试试看有没有用。\n"
        "这里面只有 3 个词：\n"
        f"1. 问题：{subject}里让你困惑的一件小事。\n"
        "2. 办法：先想一个最小解决办法。\n"
        "3. 试试：小范围试一下，看有没有变好。\n"
        f"小学生版一句话：学{subject}就是“先看见一个小问题，再试一个小办法”。\n"
        f"你现在只要回答一句话：{subject}里你最想先弄懂哪一个词？"
    )


def is_uncertain_answer(text: str) -> bool:
    compact = compact_text(text)
    return compact in {"不知道", "不清楚", "不确定", "没想好", "都可以", "随便"} or any(
        word in compact for word in ["不知道选哪个", "不确定选哪个", "没方向"]
    )


def should_start_learning_plan(text: str, learning_state: dict[str, Any]) -> bool:
    context = learning_state.get("context", {})
    level = str(learning_state.get("user_level", ""))
    enough_context = bool(context.get("purpose") and context.get("daily_time"))
    current_has_progress_info = bool(infer_learning_purpose(text) or infer_daily_time(text) or infer_user_level(text))
    return enough_context and (current_has_progress_info or is_uncertain_answer(text) or level not in {"", "待确认"})


def guided_learning_reply(
    text: str,
    history: list[dict[str, str]],
    learning_state: dict[str, Any] | None,
) -> str | None:
    if not learning_state:
        return None
    subject = str(learning_state.get("subject") or subject_from_history(history))
    if subject in {"", "这个领域", "某方面"}:
        return None
    context = learning_state.get("context", {})
    level = str(learning_state.get("user_level") or "")
    if is_uncertain_answer(text) and (context.get("purpose") or context.get("daily_time")):
        level = level if level not in {"", "待确认"} else "0基础"
        return learning_plan_reply(subject, level, context)
    if should_start_learning_plan(text, learning_state):
        level = level if level not in {"", "待确认"} else "0基础"
        return learning_plan_reply(subject, level, context)
    return None


def infer_domain(goal: str) -> str:
    text = goal.lower()
    if any(word in text for word in ["投资", "股票", "基金", "finance", "investment", "stock"]):
        return "投资研究"
    if any(word in text for word in ["创业", "startup", "商业模式", "business model"]):
        return "创业与产品开发"
    if any(word in text for word in ["求职", "面试", "resume", "job", "career"]):
        return "求职与职业发展"
    if any(word in text for word in ["咨询", "consulting"]):
        return "咨询与行业研究"
    if any(word in text for word in ["产品", "product"]):
        return "产品开发"
    return "通用业务研究"


def wants_network(text: str) -> bool:
    lowered = text.lower()
    return any(
        word in lowered
        for word in [
            "允许联网",
            "联网",
            "最新",
            "github",
            "开源项目",
            "新闻",
            "政策",
            "公司动态",
            "online",
            "web",
            "search",
        ]
    )


def should_execute(text: str) -> bool:
    raw = text.strip()
    lowered = raw.lower()
    compact = compact_text(raw)
    if lowered.startswith("/run "):
        return True
    if any(compact_text(hint) in compact for hint in NON_EXECUTE_HINTS):
        return False
    if find_execute_prefix(raw) is not None:
        return True
    return any(compact_text(phrase) in compact for phrase in EXECUTE_PHRASES)


def find_execute_prefix(text: str) -> tuple[int, int] | None:
    for prefix in EXECUTE_PREFIXES:
        pattern = rf"(^|[。！？!?；;\n\r])\s*{re.escape(prefix)}\s*[：:，, ]*"
        match = re.search(pattern, text)
        if match:
            return (match.start(), match.end())
    return None


def clean_goal(text: str) -> str:
    cleaned = re.sub(r"^/run\s+", "", text.strip(), flags=re.I)
    prefix_span = find_execute_prefix(cleaned)
    if prefix_span is not None:
        cleaned = cleaned[prefix_span[1] :]
    for phrase in EXECUTE_PHRASES:
        cleaned = re.sub(rf"^\s*{re.escape(phrase)}\s*[：:，, ]*", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned or "生成一个专家速成学习与业务执行包"


def make_task(goal: str, user_level: str = "") -> dict[str, Any]:
    domain = infer_domain(goal)
    allow_network = wants_network(goal)
    task_user_level = user_level or infer_user_level(goal) or "0基础"
    return {
        "domain": domain,
        "goal": goal,
        "question": goal,
        "user_level": task_user_level,
        "daily_time": "1小时",
        "region": "中国/全球",
        "time_range": "最近4个月",
        "no_network": not allow_network,
        "github_query": f"{domain} agent rag course github",
        "min_stars": 10,
        "github_limit": 5,
    }


def status_color(status: str) -> str:
    if status in {"completed", "done", "skipped"}:
        return Neon.GREEN
    if status in {"needs_review", "paused", "awaiting_approval", "pending_approval"}:
        return Neon.YELLOW
    if status in {"failed", "blocked"}:
        return Neon.RED
    return Neon.GREY


def summarize_state(session_id: str, runtime: HarnessRuntime, state: dict[str, Any]) -> None:
    outputs = runtime.state.outputs_dir
    report = outputs / "domain_kit_report.md"
    evaluation = outputs / "evaluation.json"
    plan = read_json_if_exists(outputs / "plan.json")
    eval_payload = read_json_if_exists(evaluation)
    rows = [
        paint("session", Neon.YELLOW) + f"    {session_id}",
        paint("状态", Neon.YELLOW)
        + "       "
        + paint(str(state.get("status", "unknown")), status_color(str(state.get("status", "")))),
        paint("学习周期", Neon.YELLOW) + f"   {plan.get('recommended_days', 'n/a')} 天",
        paint("评分", Neon.YELLOW) + f"       {eval_payload.get('score', 'n/a')}",
        paint("输出目录", Neon.YELLOW) + f"   {outputs}",
    ]
    if report.exists():
        rows.append(paint("报告", Neon.YELLOW) + f"       {report}")
    if evaluation.exists():
        rows.append(paint("评估", Neon.YELLOW) + f"       {evaluation}")
    panel("执行结果", rows, Neon.CYAN)


def execute_goal(goal: str, user_level: str = "") -> tuple[str, HarnessRuntime, dict[str, Any]]:
    task = make_task(goal, user_level=user_level)
    errors = validate_task(task)
    if errors:
        raise ValueError("; ".join(errors))

    session_id = f"study-{uuid.uuid4().hex[:8]}"
    allow_network = not task["no_network"]
    panel(
        "正在执行",
        [
            paint("目标", Neon.YELLOW) + f"       {goal}",
            paint("领域", Neon.YELLOW) + f"       {task['domain']}",
            paint("参数", Neon.YELLOW) + f"       {task['user_level']} / 每天1小时 / 中国-全球 / 最近4个月",
            paint("联网", Neon.YELLOW) + f"       {'已允许' if allow_network else '离线安全模式'}",
        ],
        Neon.ORANGE,
    )
    runtime = HarnessRuntime(ROOT, session_id)
    state = runtime.run(task, approved_tools=["github_search"] if allow_network else [])
    return session_id, runtime, state


def openai_chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def anthropic_messages_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1/messages"):
        return base
    if base.endswith("/v1"):
        return base + "/messages"
    return base + "/v1/messages"


def call_openai_compatible(config: dict[str, Any], messages: list[dict[str, str]]) -> str | None:
    base_url = str(config.get("base_url") or os.environ.get("STUDY_HACKER_BASE_URL", ""))
    model = str(config.get("model") or os.environ.get("STUDY_HACKER_MODEL", ""))
    api_key = os.environ.get(str(config.get("api_key_env", "STUDY_HACKER_API_KEY")), "")
    if not is_http_url(base_url) or not model or not api_key:
        return None
    if not api_key_send_allowed(config):
        return None

    payload = {
        "model": model,
        "messages": messages[-12:],
        "temperature": 0.4,
        "max_tokens": 700,
    }
    request = urllib.request.Request(
        openai_chat_url(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def call_anthropic(config: dict[str, Any], messages: list[dict[str, str]]) -> str | None:
    base_url = str(config.get("base_url") or os.environ.get("STUDY_HACKER_BASE_URL", ""))
    model = str(config.get("model") or os.environ.get("STUDY_HACKER_MODEL", ""))
    api_key = os.environ.get(str(config.get("api_key_env", "STUDY_HACKER_API_KEY")), "")
    if not is_http_url(base_url) or not model or not api_key:
        return None
    if not api_key_send_allowed(config):
        return None

    system = ""
    anth_messages: list[dict[str, str]] = []
    for item in messages[-12:]:
        if item["role"] == "system":
            system = item["content"]
            continue
        role = "assistant" if item["role"] == "assistant" else "user"
        anth_messages.append({"role": role, "content": item["content"]})
    payload = {
        "model": model,
        "system": system,
        "messages": anth_messages,
        "temperature": 0.4,
        "max_tokens": 700,
    }
    request = urllib.request.Request(
        anthropic_messages_url(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    parts = data.get("content", [])
    text_parts = [str(part.get("text", "")) for part in parts if part.get("type") == "text"]
    return "\n".join(part for part in text_parts if part).strip() or None


def chat_completion(messages: list[dict[str, str]]) -> str | None:
    if not api_is_configured():
        return None
    config = load_api_config()
    provider = str(config.get("provider", "")).lower()
    try:
        if provider == "anthropic":
            return call_anthropic(config, messages)
        return call_openai_compatible(config, messages)
    except (ValueError, urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        if os.environ.get("STUDY_HACKER_DEBUG_API") == "1":
            return (
                f"模型接口暂时不可用：{exc}\n"
                "我仍可用本地 harness 执行。要生成文件，请说：开始执行：你的目标。"
            )
        return None


def local_reply(
    text: str,
    latest: tuple[str, HarnessRuntime, dict[str, Any]] | None,
    history: list[dict[str, str]] | None = None,
    learning_state: dict[str, Any] | None = None,
) -> str:
    history = history or []
    lowered = text.lower().strip()
    expert_reply = expert_intake_reply(text, history)
    if expert_reply:
        return expert_reply
    guided_reply = guided_learning_reply(text, history, learning_state)
    if guided_reply:
        return guided_reply
    if any(word in lowered for word in ["你好", "您好", "嗨", "hi", "hello", "hey"]):
        return (
            "你好，我是 Study Hacker。你可以直接和我聊目标、领域、资料检索、学习路线；"
            "当你要我真正生成专家速成包时，说“开始执行：你的目标”或使用 /run。"
            "你现在想先聊哪个领域？"
        )
    if any(word in lowered for word in ["联网", "网络", "api", "key", "状态", "检查", "network", "status", "check"]):
        config = load_api_config()
        api = "已配置" if api_is_configured() else "未配置"
        if api_is_configured():
            provider = safe_config_value(config.get("provider", "n/a"))
            model = safe_config_value(config.get("model", "n/a"))
        else:
            provider = "等待首次配置"
            model = "n/a"
        return (
            f"当前 API：{api}，provider={provider}，model={model}。"
            "harness 执行默认离线安全；目标里写“允许联网”会启用资料/GitHub 检索。"
            "你这次需要最新资料和 GitHub 项目吗？"
        )
    if any(word in lowered for word in ["能做什么", "帮助", "怎么用", "功能", "help"]):
        return (
            "我可以对话解释、帮你拆目标、判断风险边界、调用 harness 生成 5-12 天专家速成包。"
            "直接说目标即可；要产出文件，用“开始执行：...”或 /run。"
            "你想先成为哪个方向的专家？"
        )
    if latest and any(word in lowered for word in ["结果", "报告", "路径", "report", "output"]):
        _, runtime, _ = latest
        report = runtime.state.outputs_dir / "domain_kit_report.md"
        return f"最近报告路径：{report}" if report.exists() else "最近一次执行还没有生成报告。"
    if learning_state:
        subject = str(learning_state.get("subject") or subject_from_history(history))
        context = learning_state.get("context", {})
        question = missing_learning_slot_question(context, str(learning_state.get("user_level", "")))
        if question:
            return f"收到，我会围绕「{subject}」推进。{question}"
        return learning_plan_reply(subject, str(learning_state.get("user_level") or "0基础"), context)
    return "收到。你可以继续补充背景；如果要我产出可验收文件，请说“开始执行：你的目标”。"


def agent_reply(
    text: str,
    latest: tuple[str, HarnessRuntime, dict[str, Any]] | None,
    history: list[dict[str, str]],
    learning_state: dict[str, Any] | None = None,
) -> str:
    learning_state = ensure_learning_state(learning_state, text, history)
    subject = (learning_state or {}).get("subject") or subject_from_history(history)
    beginner_mode = history_is_beginner_mode(history) or is_low_user_level(str((learning_state or {}).get("user_level", "")))
    if beginner_mode:
        if wants_childlike_explanation(text):
            return childlike_explanation_reply(subject)
        if mentions_job_or_time(text):
            return beginner_job_reply(subject)
    expert_reply = expert_intake_reply(text, history)
    if expert_reply:
        return expert_reply
    level = infer_user_level(text)
    if level and subject != "这个领域":
        if is_low_user_level(level):
            return beginner_foundation_reply(subject, level, (learning_state or {}).get("context", {}))
        if (learning_state or {}).get("context", {}).get("purpose") and (learning_state or {}).get("context", {}).get("daily_time"):
            return learning_plan_reply(subject, level, (learning_state or {}).get("context", {}))
        return experienced_foundation_reply(subject, level)
    guided_reply = guided_learning_reply(text, history, learning_state)
    if guided_reply:
        return guided_reply
    system = (
        "你是 Study Hacker，一个中文为主的专家速成 Agent。"
        "你和用户直接聊天，不使用问卷式脚本。"
        "当用户表达“想成为某方面的专家/高手/顾问/分析师”等意图时，先主动询问用户了解程度；"
        "如果用户是 0 基础、小白、只听过概念或明显低基础，先用通俗比喻或小故事解释基础概念，"
        "不要一开始布置高难任务；先给一句话定义，然后最多引入 3 个新词。"
        "低基础首轮任务必须极轻：记住一句定义、理解 3 个词、说 1 个生活例子；不要要求建立 10 个术语卡。"
        "不要把学习领域和用途混在一起问；应用场景要问：找工作、做项目、创业、做研究。"
        "涉及求职时，先问用户背景、偏好和是否愿意写代码，不要直接假设产品经理最适合。"
        "不要为了形式在每个回答结尾都反问。只有缺少会阻塞下一步的关键信息时才问；信息足够时直接制定计划、讲解或推进练习。"
        "如果用户已经说过用途、每天投入时间或基础水平，不要重复询问同一信息。"
        "你可以建议用户用“开始执行：目标”或 /run 来调用本地 harness 生成文件。"
        "回答简洁、实战、中文为主，必要的命令和技术词可用英文。"
        "不要声称已经执行工具，除非外层程序已经执行。"
        + learning_outline_prompt(learning_state)
    )
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": text}]
    response = chat_completion(messages)
    return response or local_reply(text, latest, history, learning_state)


def prompt_line(latest: tuple[str, HarnessRuntime, dict[str, Any]] | None) -> str:
    left = paint("study", Neon.CYAN) + paint("@", Neon.GREY) + paint("hacker", Neon.PINK)
    if latest:
        session_id, _, state = latest
        status = str(state.get("status", "idle"))
        return left + paint(f" [{session_id}:{status}]", Neon.GREY) + paint(" > ", Neon.YELLOW)
    return left + paint(" > ", Neon.YELLOW)


def interactive(initial_goal: str = "") -> int:
    enable_windows_ansi()
    banner()
    boot_sequence()
    configure_api()
    dashboard()
    print(paint("你好，我已进入直接对话模式。你可以直接说话；要产出文件时说“开始执行：...”。", Neon.BOLD))
    print()

    latest: tuple[str, HarnessRuntime, dict[str, Any]] | None = None
    history: list[dict[str, str]] = []
    learning_state: dict[str, Any] | None = None
    pending = initial_goal.strip()
    while True:
        try:
            raw = pending or input(prompt_line(latest)).strip()
            pending = ""
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue
        learning_state = ensure_learning_state(learning_state, raw, history)

        command = raw.lower()
        if command in {"/exit", "exit", "quit", "/quit"}:
            print(paint("会话已关闭。", Neon.GREY))
            return 0
        if command in {"/help", "help"}:
            help_text()
            continue
        if command == "/config":
            configure_api(force=True)
            dashboard()
            continue
        if command == "/status":
            if not latest:
                panel("暂无 session", ["还没有执行过 harness。你可以用 /run <目标>。"], Neon.ORANGE)
            else:
                session_id, runtime, _ = latest
                latest = (session_id, runtime, runtime.state.read())
                summarize_state(*latest)
            continue
        if command == "/open":
            if not latest:
                panel("暂无报告", ["还没有生成报告。"], Neon.ORANGE)
            else:
                _, runtime, _ = latest
                report = runtime.state.outputs_dir / "domain_kit_report.md"
                panel("报告路径", [str(report) if report.exists() else "报告尚未生成。"], Neon.CYAN)
            continue

        if should_execute(raw):
            goal = clean_goal(raw)
            try:
                user_level = conversation_user_level(history, raw)
                latest = execute_goal(goal, user_level=user_level)
                summarize_state(*latest)
                panel(
                    "下一步追问",
                    [
                        "你想先让我解释报告里的基础概念，还是继续把它改成一个可提交的业务交付物？",
                        "如果你是低基础，我会先从术语、地图和生活化案例开始，不直接加难度。",
                    ],
                    Neon.GREEN,
                )
            except Exception as exc:  # noqa: BLE001
                panel("执行错误", [str(exc)], Neon.RED)
            continue

        show_thinking()
        try:
            learning_state = advance_learning_state(learning_state, raw)
            reply = agent_reply(raw, latest, history, learning_state)
        finally:
            clear_thinking()
        panel("Study Hacker", reply.splitlines() or [reply], Neon.VIOLET)
        history.append({"role": "user", "content": raw})
        history.append({"role": "assistant", "content": reply})
        history = history[-10:]


def main() -> int:
    parser = argparse.ArgumentParser(prog="study")
    sub = parser.add_subparsers(dest="command")
    hacker = sub.add_parser("hacker", help="start the Study Hacker interactive agent")
    hacker.add_argument("goal", nargs="*", help="optional first message or /run goal")
    hacker.add_argument("--version", action="store_true")
    hacker.add_argument("--reset-config", action="store_true", help="remove local first-run API config before starting")
    args = parser.parse_args()

    if args.command == "hacker":
        if args.version:
            print(f"study hacker {VERSION}")
            return 0
        if args.reset_config:
            for path in (CONFIG_PATH, ENV_PATH):
                if path.exists():
                    path.unlink()
        return interactive(" ".join(args.goal))

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
