"""
Pytest 配置和共享 fixtures
"""
import pytest
import asyncio
from typing import Generator
from pathlib import Path


@pytest.fixture
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_polymarket_bin(tmp_path: Path) -> str:
    """创建模拟的 polymarket 二进制文件"""
    script = tmp_path / "polymarket"
    script.write_text("""#!/bin/bash
echo '{"status": "ok", "data": []}'
""")
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def mock_polymarket_bin_slow(tmp_path: Path) -> str:
    """创建一个执行缓慢的模拟 polymarket 二进制"""
    script = tmp_path / "polymarket_slow"
    script.write_text("""#!/bin/bash
sleep 10
echo '{"status": "ok"}'
""")
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def mock_polymarket_bin_fail(tmp_path: Path) -> str:
    """创建一个会失败的模拟 polymarket 二进制"""
    script = tmp_path / "polymarket_fail"
    script.write_text("""#!/bin/bash
echo "error message" >&2
exit 1
""")
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def mock_polymarket_bin_empty(tmp_path: Path) -> str:
    """创建一个返回空响应的模拟 polymarket 二进制"""
    script = tmp_path / "polymarket_empty"
    script.write_text("""#!/bin/bash
exit 0
""")
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def mock_polymarket_bin_invalid_json(tmp_path: Path) -> str:
    """创建一个返回无效 JSON 的模拟 polymarket 二进制"""
    script = tmp_path / "polymarket_invalid"
    script.write_text("""#!/bin/bash
echo "not a json"
""")
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def valid_private_key() -> str:
    """有效的私钥（用于测试）"""
    return "0x" + "a" * 64


@pytest.fixture
def placeholder_keys() -> list[str]:
    """Placeholder 私钥列表"""
    return [
        "0x" + "0" * 64,
        "0x" + "f" * 64,
        "__PLACEHOLDER__",
        "YOUR_PRIVATE_KEY",
        "TEST_KEY"
    ]


@pytest.fixture
def short_key() -> str:
    """长度不足的私钥"""
    return "0x" + "a" * 32


@pytest.fixture
def invalid_hex_key() -> str:
    """包含非十六进制字符的私钥"""
    return "0x" + "z" * 64
