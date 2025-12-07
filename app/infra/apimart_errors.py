"""
Apimart 错误处理和重试逻辑

实现：
- 自定义异常类
- 错误处理器（处理 400/401/402/429/5xx 错误）
- 指数退避重试策略
"""

import asyncio
import logging
from enum import Enum
from typing import Callable, TypeVar, ParamSpec

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class ApimartErrorCode(str, Enum):
    """Apimart 错误码"""

    PARAM_ERROR = "apimart_param_error"
    AUTH_ERROR = "apimart_auth_error"
    INSUFFICIENT_BALANCE = "apimart_insufficient_balance"
    RATE_LIMITED = "apimart_rate_limited"
    SERVER_ERROR = "apimart_server_error"
    TIMEOUT = "apimart_timeout"
    UNKNOWN = "apimart_unknown_error"


class ApimartError(Exception):
    """Apimart API 错误基类"""

    def __init__(
        self,
        message: str,
        error_code: ApimartErrorCode,
        status_code: int | None = None,
        should_alert: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.should_alert = should_alert

    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"


class ApimartParamError(ApimartError):
    """参数错误 (400)"""

    def __init__(self, message: str = "Invalid request parameters"):
        super().__init__(
            message=message,
            error_code=ApimartErrorCode.PARAM_ERROR,
            status_code=400,
            should_alert=False,
        )


class ApimartAuthError(ApimartError):
    """鉴权错误 (401)"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code=ApimartErrorCode.AUTH_ERROR,
            status_code=401,
            should_alert=True,
        )


class ApimartInsufficientBalanceError(ApimartError):
    """余额不足 (402)"""

    def __init__(self, message: str = "Insufficient balance"):
        super().__init__(
            message=message,
            error_code=ApimartErrorCode.INSUFFICIENT_BALANCE,
            status_code=402,
            should_alert=True,
        )


class ApimartRateLimitError(ApimartError):
    """频率限制 (429)"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code=ApimartErrorCode.RATE_LIMITED,
            status_code=429,
            should_alert=False,
        )


class ApimartServerError(ApimartError):
    """服务器错误 (5xx)"""

    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(
            message=message,
            error_code=ApimartErrorCode.SERVER_ERROR,
            status_code=status_code,
            should_alert=False,
        )


class ApimartErrorHandler:
    """Apimart 错误处理器"""

    @staticmethod
    def handle_response_error(response: httpx.Response) -> None:
        """
        处理 HTTP 响应错误

        Args:
            response: httpx 响应对象

        Raises:
            ApimartError: 根据状态码抛出对应的错误
        """
        status_code = response.status_code

        if status_code < 400:
            return

        try:
            error_detail = response.json().get("error", response.text)
        except Exception:
            error_detail = response.text

        match status_code:
            case 400:
                raise ApimartParamError(f"Parameter error: {error_detail}")
            case 401:
                raise ApimartAuthError(f"Authentication failed: {error_detail}")
            case 402:
                raise ApimartInsufficientBalanceError(
                    f"Insufficient balance: {error_detail}"
                )
            case 429:
                raise ApimartRateLimitError(f"Rate limit exceeded: {error_detail}")
            case _ if status_code >= 500:
                raise ApimartServerError(
                    f"Server error: {error_detail}", status_code=status_code
                )
            case _:
                raise ApimartError(
                    message=f"Unexpected error: {error_detail}",
                    error_code=ApimartErrorCode.UNKNOWN,
                    status_code=status_code,
                )

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """
        判断错误是否可重试

        Args:
            error: 异常对象

        Returns:
            bool: 是否可重试
        """
        if isinstance(error, ApimartRateLimitError):
            return True
        if isinstance(error, ApimartServerError):
            return True
        if isinstance(error, httpx.TimeoutException):
            return True
        if isinstance(error, httpx.ConnectError):
            return True
        return False


async def with_retry(
    func: Callable[P, T],
    *args: P.args,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    **kwargs: P.kwargs,
) -> T:
    """
    带指数退避重试的函数执行器

    Args:
        func: 要执行的异步函数
        *args: 函数位置参数
        max_attempts: 最大重试次数，默认从配置读取
        base_delay: 基础延迟（秒），默认从配置读取
        max_delay: 最大延迟（秒），默认从配置读取
        **kwargs: 函数关键字参数

    Returns:
        函数返回值

    Raises:
        ApimartError: 重试耗尽后抛出最后一个错误
    """
    settings = get_settings()
    max_attempts = max_attempts or settings.retry_max_attempts
    base_delay = base_delay or settings.retry_base_delay
    max_delay = max_delay or settings.retry_max_delay

    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e

            if not ApimartErrorHandler.is_retryable(e):
                raise

            if attempt == max_attempts - 1:
                logger.error(
                    f"Retry exhausted after {max_attempts} attempts: {e}"
                )
                raise

            # 指数退避计算
            delay = min(base_delay * (2**attempt), max_delay)
            logger.warning(
                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    # 理论上不会到达这里，但为了类型安全
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")


async def with_rate_limit_retry(
    func: Callable[P, T],
    *args: P.args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs: P.kwargs,
) -> T:
    """
    专门处理 429 频率限制的重试器

    使用固定间隔重试，最多 3 次，间隔 1-2 秒

    Args:
        func: 要执行的异步函数
        *args: 函数位置参数
        max_attempts: 最大重试次数，默认 3
        base_delay: 基础延迟（秒），默认 1.0
        **kwargs: 函数关键字参数

    Returns:
        函数返回值

    Raises:
        ApimartRateLimitError: 重试耗尽后抛出
    """
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except ApimartRateLimitError as e:
            last_error = e

            if attempt == max_attempts - 1:
                logger.error(
                    f"Rate limit retry exhausted after {max_attempts} attempts"
                )
                raise

            delay = base_delay + (attempt * 0.5)  # 1.0, 1.5, 2.0 秒
            logger.warning(
                f"Rate limited, attempt {attempt + 1}/{max_attempts}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
        except Exception:
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")
