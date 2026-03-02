"""
Retry 模块测试
"""
import pytest
import asyncio
from openclaw_polymarket_skill.retry import (
    async_retry,
    RetryConfig,
    should_retry,
    calculate_delay,
)


class TestShouldRetry:
    """重试判断逻辑测试"""

    def test_timeout_error_should_retry(self) -> None:
        """测试 TimeoutError 应该重试"""
        assert should_retry(asyncio.TimeoutError()) is True

    def test_connection_error_should_retry(self) -> None:
        """测试 ConnectionError 应该重试"""
        assert should_retry(ConnectionError()) is True

    def test_os_error_should_retry(self) -> None:
        """测试 OSError 应该重试"""
        assert should_retry(OSError()) is True

    def test_value_error_should_not_retry(self) -> None:
        """测试 ValueError 不应该重试"""
        assert should_retry(ValueError()) is False

    def test_key_error_should_not_retry(self) -> None:
        """测试 KeyError 不应该重试"""
        assert should_retry(KeyError()) is False


class TestCalculateDelay:
    """延迟计算测试"""

    def test_initial_delay(self) -> None:
        """测试初始延迟"""
        config = RetryConfig(initial_delay=1.0, jitter=False)
        delay = calculate_delay(0, config)
        assert delay == 1.0

    def test_exponential_backoff(self) -> None:
        """测试指数退避"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, jitter=False)
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0

    def test_max_delay_cap(self) -> None:
        """测试最大延迟限制"""
        config = RetryConfig(initial_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)
        delay = calculate_delay(10, config)  # 1 * 2^10 = 1024，应被限制到 5.0
        assert delay == 5.0

    def test_jitter_adds_randomness(self) -> None:
        """测试抖动添加随机性"""
        config = RetryConfig(initial_delay=10.0, jitter=True)
        delay1 = calculate_delay(0, config)
        delay2 = calculate_delay(0, config)

        # 延迟应该在 50%-100% 范围内
        assert 5.0 <= delay1 <= 10.0
        assert 5.0 <= delay2 <= 10.0

        # 由于随机性，两次计算结果很可能不同（虽然有小概率相同）
        # 这里只检查范围，不检查是否不同


class TestAsyncRetry:
    """异步重试装饰器测试"""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self) -> None:
        """测试首次成功无需重试"""
        call_count = 0

        @async_retry(RetryConfig(max_attempts=3))
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        """测试超时自动重试"""
        call_count = 0

        @async_retry(RetryConfig(max_attempts=3, initial_delay=0.1))
        async def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("timeout")
            return "success"

        result = await timeout_then_success()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_value_error(self) -> None:
        """测试非网络错误不重试"""
        call_count = 0

        @async_retry(RetryConfig(max_attempts=3))
        async def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("business logic error")

        with pytest.raises(ValueError):
            await value_error_func()

        assert call_count == 1  # 不重试

    @pytest.mark.asyncio
    async def test_max_attempts_reached(self) -> None:
        """测试达到最大重试次数"""
        call_count = 0

        @async_retry(RetryConfig(max_attempts=3, initial_delay=0.1))
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("timeout")

        with pytest.raises(asyncio.TimeoutError):
            await always_fail()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_connection_error(self) -> None:
        """测试连接错误重试"""
        call_count = 0

        @async_retry(RetryConfig(max_attempts=2, initial_delay=0.1))
        async def connection_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("connection failed")
            return "success"

        result = await connection_error_then_success()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_default_config(self) -> None:
        """测试默认配置"""
        call_count = 0

        @async_retry()  # 使用默认配置
        async def func_with_defaults():
            nonlocal call_count
            call_count += 1
            return call_count

        result = await func_with_defaults()
        assert result == 1
        assert call_count == 1
