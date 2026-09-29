"""Timeout cap for direct_api_call: the non-streaming SDK timeout must stay
below the cron inactivity watchdog (HERMES_CRON_TIMEOUT, default 600s).

Without the cap, the default 1800s SDK timeout outlives the 600s watchdog:
a slow/hung provider gets the whole cron job killed as "idle" instead of
raising a retryable timeout error. Regression test for the delegate_task
subagent stall observed 2026-09-29 ("idle for 604s" while legitimately
waiting on the provider).
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agent.chat_completion_helpers import direct_api_call


def _make_agent():
    agent = MagicMock()
    agent.platform = "cron"
    agent.api_mode = "chat_completions"
    agent.provider = "custom"
    agent._interrupt_requested = False
    agent._touch_activity = MagicMock()
    agent._close_request_openai_client = MagicMock()
    return agent


def _run_with_timeout(agent, timeout_in, env_cron_timeout=None):
    seen = {}
    fake_client = MagicMock()

    def _create(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(id="ok")

    fake_client.chat.completions.create.side_effect = _create
    agent._create_request_openai_client = MagicMock(return_value=fake_client)

    kwargs = {"model": "m", "messages": []}
    if timeout_in is not None:
        kwargs["timeout"] = timeout_in

    env = {}
    if env_cron_timeout is not None:
        env["HERMES_CRON_TIMEOUT"] = str(env_cron_timeout)
    # Ensure a clean default when not specified
    with patch.dict(os.environ, env, clear=False):
        if env_cron_timeout is None:
            os.environ.pop("HERMES_CRON_TIMEOUT", None)
        direct_api_call(agent, kwargs)
    return seen.get("timeout"), kwargs.get("timeout")


def test_default_cap_is_540():
    agent = _make_agent()
    sent, original = _run_with_timeout(agent, 1800.0)
    assert sent == 540.0, f"expected 540 cap, got {sent}"
    assert original == 1800.0, "caller's dict must not be mutated"


def test_tighter_provider_timeout_is_respected():
    agent = _make_agent()
    sent, _ = _run_with_timeout(agent, 120.0)
    assert sent == 120.0, f"expected 120 (provider config wins), got {sent}"


def test_missing_timeout_gets_cap():
    agent = _make_agent()
    sent, _ = _run_with_timeout(agent, None)
    assert sent == 540.0, f"expected 540 cap, got {sent}"


def test_custom_cron_timeout_respected():
    agent = _make_agent()
    sent, _ = _run_with_timeout(agent, 5000.0, env_cron_timeout=3600)
    assert sent == 3540.0, f"expected 3540, got {sent}"
    # ...and a timeout already under the cap is left alone
    sent2, _ = _run_with_timeout(agent, 1800.0, env_cron_timeout=3600)
    assert sent2 == 1800.0, f"expected 1800 untouched, got {sent2}"


def test_unlimited_cron_timeout_means_no_cap():
    agent = _make_agent()
    sent, _ = _run_with_timeout(agent, 1800.0, env_cron_timeout=0)
    assert sent == 1800.0, f"expected no cap (1800), got {sent}"
