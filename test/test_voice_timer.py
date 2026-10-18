"""语音定时器解析单测：python test/test_voice_timer.py 或 pytest test/test_voice_timer.py"""

from datetime import datetime

from xiaomusic.voice_timer import (
    cron_expression_for,
    native_timer_failed,
    parse_voice_timer,
)


def test_minutes():
    assert parse_voice_timer("5分钟后关闭风扇") == (300, "关闭风扇", "5分钟")


def test_minutes_with_space():
    assert parse_voice_timer("5 分钟后 关闭风扇") == (300, "关闭风扇", "5分钟")


def test_hours():
    assert parse_voice_timer("2小时后打开客厅灯") == (7200, "打开客厅灯", "2小时")


def test_chinese_numerals():
    assert parse_voice_timer("五分钟后关闭风扇") == (300, "关闭风扇", "五分钟")
    assert parse_voice_timer("两小时后提醒我喝水") == (7200, "提醒我喝水", "两小时")
    assert parse_voice_timer("十分钟后关灯") == (600, "关灯", "十分钟")


def test_half_hour():
    assert parse_voice_timer("半小时后关闭风扇") == (1800, "关闭风扇", "半小时")
    assert parse_voice_timer("半个小时后关闭风扇") == (1800, "关闭风扇", "半小时")


def test_one_and_half_hour():
    assert parse_voice_timer("一个半小时后关闭风扇") == (5400, "关闭风扇", "一个半小时")


def test_nested_time_in_action():
    # action 里再带时间描述也不影响外层解析
    assert parse_voice_timer("5分钟后提醒我10分钟后开会") == (
        300,
        "提醒我10分钟后开会",
        "5分钟",
    )


def test_music_action():
    # 动作可以是 xiaomusic 自己的指令，到点走 run_voice_command 先匹配
    assert parse_voice_timer("10分钟后停止播放") == (600, "停止播放", "10分钟")


def test_invalid():
    assert parse_voice_timer("关闭风扇") is None
    assert parse_voice_timer("5分钟后") is None
    assert parse_voice_timer("0分钟后关闭风扇") is None
    assert parse_voice_timer("") is None
    assert parse_voice_timer(None) is None
    assert parse_voice_timer("5秒后关闭风扇") is None  # v1 不支持秒


def test_cron_expression():
    assert cron_expression_for(datetime(2026, 10, 16, 18, 54)) == "54 18 16 10 *"
    assert cron_expression_for(datetime(2026, 1, 5, 0, 3)) == "3 0 5 1 *"


def test_native_timer_failed():
    # 只有原生明确说处理不了才接管（实测原话）
    assert native_timer_failed("没有发现可以操作的设备，先去米家绑定设备吧。") is True
    assert native_timer_failed("找不到设备，请去米家先添加设备吧") is True
    # 认出设备类型时小爱用具体设备词（实测 2026-10-17："电风扇"），前缀匹配同样接管
    assert native_timer_failed("没有发现可以操作的电风扇，先去米家绑定设备吧。") is True
    assert native_timer_failed("没有发现可以操作的空调，先去米家绑定设备吧。") is True
    # 即使前半句换说法，只要尾巴是"先去米家绑定设备吧"就接管
    assert native_timer_failed("抱歉，当前设备不支持定时，先去米家绑定设备吧。") is True
    # 2026-10-18 用户实测原话②（"一分钟后关闭餐厅风扇"）：房间名/设备名可变
    assert (
        native_timer_failed(
            "餐厅没有找到可控制的电风扇，去手机米家把它添加到房间里吧。"
        )
        is True
    )
    # 原生能处理的（灯/电视等）：不接管，避免重复执行
    assert native_timer_failed("好的，已为你设置5分钟后关闭客厅灯") is False
    assert native_timer_failed("好的") is False
    # 无回复/回复不明：保守起见不接管
    assert native_timer_failed("") is False
    assert native_timer_failed(None) is False


if __name__ == "__main__":
    cases = sorted(
        [(k, v) for k, v in globals().items() if k.startswith("test_")],
        key=lambda kv: kv[0],
    )
    for name, fn in cases:
        fn()
        print(f"{name} ok")
    print(f"all {len(cases)} voice_timer tests passed")
