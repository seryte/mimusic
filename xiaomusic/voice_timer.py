"""语音定时器

把"5分钟后关闭风扇"这类口令解析为一次性定时任务。

背景：红外设备等非米家在线设备，小爱原生不支持"X分钟后做Y"
（会报"找不到设备，请去米家先添加设备吧"），但支持即时指令（如"关闭风扇"）。
xiaomusic 在对话流里拦截定时口令，自动生成一次性 cron 表达式并创建任务，
到点用 native 通道执行原指令。

v1 支持的说法：
- "N分钟后..." / "N小时后..."（N 支持阿拉伯数字与中文数字，如 5分钟后、五分钟后、两小时后）
- "半小时后..." / "一个半小时后..."
"""

import re
from datetime import datetime

from xiaomusic.utils.text_utils import chinese_to_number

# 最长支持 7 天，超过的由调用方拒绝（避免无意义的远期任务）
MAX_DELAY_SECONDS = 7 * 24 * 3600

_NUM = r"(\d+|[零一二两三四五六七八九十百]+)"

# (正则, 每单位秒数, 固定秒数, 固定描述)
# 前两项带数字组；后两项只有 action 组，走固定秒数
_TIMER_PATTERNS = [
    (re.compile(rf"^{_NUM}\s*分钟后(.+)$"), 60, None, None),
    (re.compile(rf"^{_NUM}\s*小时后(.+)$"), 3600, None, None),
    (re.compile(r"^半\s*个?\s*小时后(.+)$"), None, 1800, "半小时"),
    (
        re.compile(r"^(?:一\s*个\s*半|1\s*个\s*半)\s*小时后(.+)$"),
        None,
        5400,
        "一个半小时",
    ),
]


def _parse_number(raw: str):
    """数字字符串转 int，支持阿拉伯数字与中文数字；非法返回 None。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    try:
        n = chinese_to_number(raw.replace("两", "二"))
        return n if n > 0 else None
    except Exception:
        return None


def parse_voice_timer(query):
    """解析语音定时口令。

    Args:
        query: 如 "5分钟后关闭风扇"

    Returns:
        (delay_seconds, action, delay_text)；不是定时口令或不合法时返回 None。
        delay_text 如 "5分钟"/"半小时"，用于 TTS 确认。
    """
    text = (query or "").strip()
    for pattern, unit, fixed_secs, fixed_text in _TIMER_PATTERNS:
        m = pattern.match(text)
        if not m:
            continue
        groups = m.groups()
        if unit is None:
            action = groups[0].strip()
            return (fixed_secs, action, fixed_text) if action else None
        num = _parse_number(groups[0])
        action = groups[1].strip()
        if num is None or num <= 0 or not action:
            return None
        unit_text = "分钟" if unit == 60 else "小时"
        return num * unit, action, f"{groups[0].strip()}{unit_text}"
    return None


def cron_expression_for(fire_at: datetime) -> str:
    """为一次性任务生成 cron 表达式（分 时 日 月 周）。

    注意：表达式本身是周期语义，调用方必须在首次执行后删除任务，
    否则每年同一时刻会再触发一次。
    """
    return f"{fire_at.minute} {fire_at.hour} {fire_at.day} {fire_at.month} *"


# 小爱原生处理定时失败时的回复特征（保守匹配：只认这种明确表述）
# 实测原话："没有发现可以操作的设备，先去米家绑定设备吧。"
NATIVE_TIMER_UNSUPPORTED_HINTS = ("没有发现可以操作的设备", "找不到设备")


def native_timer_failed(answer) -> bool:
    """判断小爱原生是否明确表示处理不了这条定时口令。

    保守策略：无回复或回复不明时返回 False（不接管），避免误伤原生支持的设备。
    """
    if not answer:
        return False
    return any(h in answer for h in NATIVE_TIMER_UNSUPPORTED_HINTS)
