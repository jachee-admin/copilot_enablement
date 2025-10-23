# Prompt: Robust Retry with Exponential Backoff + Jitter (Python)

## Goal
Generate a small, production-ready Python utility that retries transient operations using **exponential backoff + jitter** with:
- Max attempts (bounded)
- Base delay and cap (ceiling)
- Full jitter (randomized wait) to avoid thundering herd
- Logging hooks
- Exception filtering (retry only on specific errors)
- Sync function wrapper + decorator variant
- Testable, readable code

## Context (include when prompting Copilot)
- Python 3.10+
- Standard library only (unless otherwise stated)
- Thread-safe randomness acceptable via `random`
- Should not swallow exceptions silently; on final failure, re-raise the last error
- Jitter strategy: **Full jitter** (sleep = random(0, current_backoff)), capped at `max_delay`
- Accept list/tuple of exception types to retry
- Provide an example usage with a flaky function (e.g., HTTP call placeholder)

## Primary Prompt (paste this to Copilot)
> Write a Python module named `retry.py` that implements a robust retry helper with exponential backoff and full jitter.
> Requirements:
> - Function: `retry(fn, *, max_attempts=5, base_delay=0.25, max_delay=8.0, retry_exceptions=(Exception,), on_retry=None)`
> - Behavior: Call `fn()`. On exception matching `retry_exceptions`, sleep using exponential backoff with full jitter, then retry, up to `max_attempts`.
> - Backoff: `delay = min(max_delay, base_delay * (2 ** (attempt - 1)))`; sleep `random.uniform(0, delay)`.
> - If `on_retry` is provided, call it with `(attempt, exc, sleep_s)`.
> - After exhausting attempts, re-raise the last exception.
> - Provide a decorator `@with_retry(...)` that applies the same policy to a callable.
> - Include a `main` block with a demo `fetch()` that fails randomly and shows logging output.
> - Include type hints and docstrings.
> - Keep the code standard-library only.
>

## Acceptance Criteria
- Deterministic parameters; randomness only in jitter
- Clean separation of policy vs. action (retry wrapper doesn’t know business logic)
- Final error is not masked
- Easy to unit test (inject a fake clock via an optional sleep function if you like)
- MyPy-friendly type hints

## Reference Script
```python
# retry.py
from __future__ import annotations
from typing import Callable, Iterable, Type, TypeVar, ParamSpec
import random
import time
import logging

T = TypeVar("T")
P = ParamSpec("P")
logger = logging.getLogger(__name__)

def retry(
    fn: Callable[P, T],
    *,
    max_attempts: int = 5,
    base_delay: float = 0.25,
    max_delay: float = 8.0,
    retry_exceptions: Iterable[Type[BaseException]] = (Exception,),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    _sleep: Callable[[float], None] = time.sleep,  # for testability
) -> T:
    """
    Call `fn()` with exponential backoff + full jitter on transient errors.

    Args:
        fn: zero-arg callable (wrap with lambda for args) to execute.
        max_attempts: total tries including the first.
        base_delay: initial backoff (seconds).
        max_delay: cap for backoff (seconds).
        retry_exceptions: iterable of exception types that warrant a retry.
        on_retry: callback(attempt, exc, sleep_s) invoked before sleeping.
        _sleep: sleep function (injectable for testing).

    Returns:
        The return value of `fn()` if it eventually succeeds.

    Raises:
        The last exception after exhausting attempts.
    """
    attempt = 0
    last_exc: BaseException | None = None

    while attempt < max_attempts:
        try:
            return fn()
        except tuple(retry_exceptions) as exc:
            attempt += 1
            last_exc = exc
            if attempt >= max_attempts:
                break

            # Exponential backoff (1, 2, 4, ...), capped
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            # Full jitter: random in [0, delay]
            sleep_s = random.uniform(0, delay)

            if on_retry:
                try:
                    on_retry(attempt, exc, sleep_s)
                except Exception:  # guardrail: never break retries on callback failure
                    logger.debug("on_retry callback failed", exc_info=True)

            logger.debug("Retry attempt %d after %s: sleeping %.2fs", attempt, exc, sleep_s)
            _sleep(sleep_s)
        except BaseException:
            # Non-retryable exception
            raise

    assert last_exc is not None
    raise last_exc


def with_retry(
    *,
    max_attempts: int = 5,
    base_delay: float = 0.25,
    max_delay: float = 8.0,
    retry_exceptions: Iterable[Type[BaseException]] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator applying the same retry policy to a function.
    """
    def deco(fn: Callable[P, T]) -> Callable[P, T]:
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            return retry(
                lambda: fn(*args, **kwargs),
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                retry_exceptions=retry_exceptions,
                on_retry=lambda attempt, exc, sleep_s: logging.getLogger(__name__).info(
                    "Attempt %d failed with %r; retrying in %.2fs", attempt, exc, sleep_s
                ),
            )
        return wrapped
    return deco


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import random as _r

    @with_retry(max_attempts=4, base_delay=0.2, max_delay=2.0, retry_exceptions=(RuntimeError,))
    def fetch() -> str:
        # Simulate flaky operation
        if _r.random() < 0.7:
            raise RuntimeError("Transient failure")
        return "OK"

    try:
        print(fetch())
    except RuntimeError as e:
        logger.error("Operation failed after retries: %s", e)
```

## Quick Review Checklist (for this artifact)

* [ ] Retries only on whitelisted exceptions
* [ ] Backoff grows exponentially; capped
* [ ] Jitter applied (randomized)
* [ ] Final failure re-raises last exception
* [ ] Logging/reporting hooks present
* [ ] Decorator variant provided
* [ ] Testable (injectable sleep)

## Follow-up Refinement Prompts

* “Add support for async functions with `asyncio.sleep` and `async def` equivalents.”
* “Add a context manager to record attempt metrics (attempt count, total wait, last exception).”
* “Make `retry_exceptions` accept callables for conditional retry (e.g., HTTP 5xx only).”
* “Add unit tests using a fake clock and deterministic random via `random.Random(0)`.”

## Notes & Pitfalls

* **Full vs. equal jitter:** Full jitter reduces herd effects better than fixed or equal jitter.
* **Do not** catch `BaseException` for retry; keep `KeyboardInterrupt/SystemExit` unhandled for safety.
* In high-QPS services, prefer per-call RNG (or thread-local RNG) if global `random` is contentious.

```

If you want the async variant, I can generate a clean `async_retry.py` next—or we can fill another file from your list (e.g., `ansible/deploy_postgres_prompt.md`).

```
