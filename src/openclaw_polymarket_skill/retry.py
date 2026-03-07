"""
重试机制模块
"""
from __future__ import annotations

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Args:
            max_attempts: 最大尝试次数
            initial_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数退避基数
            jitter: 是否添加抖动
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def should_retry(exception: Exception) -> bool:
    """
    判断异常是否应该重试

    只重试网络相关错误，不重试业务逻辑错误

    Args:
        exception: 异常对象

    Returns:
        True 如果应该重试，否则 False
    """
    retryable_errors = (
        asyncio.TimeoutError,
        ConnectionError,
        ConnectionRefusedError,
        ConnectionResetError,
        OSError,
    )
    return isinstance(exception, retryable_errors)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    计算重试延迟（指数退避 + 抖动）

    Args:
        attempt: 当前尝试次数（从0开始）
        config: 重试配置

    Returns:
        延迟时长（秒）
    """
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )

    if config.jitter:
        # 添加 50%-100% 的抖动
        delay = delay * (0.5 + random.random() * 0.5)

    return delay


def async_retry(config: Optional[RetryConfig] = None):
    """
    异步重试装饰器

    使用示例:
        @async_retry(RetryConfig(max_attempts=3))
        async def fetch_data():
            # 可能失败的操作
            ...

    Args:
        config: 重试配置，默认使用 RetryConfig()

    Returns:
        装饰器函数
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)

                    # 首次重试成功后记录日志
                    if attempt > 0:
                        logger.info(
                            f"Retry successful on attempt {attempt + 1}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "total_attempts": config.max_attempts
                            }
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    # 判断是否应该重试
                    if not should_retry(e):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "error_type": type(e).__name__
                            }
                        )
                        raise

                    # 最后一次尝试失败
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "last_error": str(e),
                                "error_type": type(e).__name__
                            }
                        )
                        raise

                    # 计算延迟并等待
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}, "
                        f"retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "delay_seconds": delay
                        }
                    )
                    await asyncio.sleep(delay)

            # 理论上不会到达这里
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")

        return wrapper
    return decorator


class RetryableOperation:
    """
    可重试操作的上下文管理器

    使用示例:
        async with RetryableOperation(config) as retry:
            result = await retry.execute(some_async_function, arg1, arg2)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        执行可重试操作

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        @async_retry(self.config)
        async def _wrapped():
            return await func(*args, **kwargs)

        return await _wrapped()
