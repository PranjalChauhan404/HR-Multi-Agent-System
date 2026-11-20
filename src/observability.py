from functools import wraps

from src.config import LANGFUSE_ENABLED


def trace_function(name: str, as_type: str = "span"):
    """
    Add Langfuse tracing when credentials are configured.

    Raw function inputs and outputs are not automatically captured.
    The application continues to work when Langfuse is disabled.
    """

    def decorator(func):
        if not LANGFUSE_ENABLED:
            return func

        try:
            from langfuse import observe

            traced_func = observe(
                name=name,
                as_type=as_type,
                capture_input=False,
                capture_output=False,
            )(func)

            return traced_func

        except Exception as exc:
            print(
                f"[Observability] Could not trace {name}: "
                f"{type(exc).__name__}: {exc}"
            )

            @wraps(func)
            def fallback(*args, **kwargs):
                return func(*args, **kwargs)

            return fallback

    return decorator