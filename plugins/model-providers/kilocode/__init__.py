"""Kilo Code provider profile — filters to :free models only."""

from providers import register_provider
from providers.base import ProviderProfile


class KiloCodeFreeProvider(ProviderProfile):
    """KiloCode provider that only exposes :free models in the picker."""

    name = "kilocode"
    aliases = ("kilo-code", "kilo", "kilo-gateway")
    env_vars = ("KILOCODE_API_KEY",)
    base_url = "https://api.kilo.ai/api/gateway"
    default_aux_model = "google/gemini-3.6-flash"

    def fetch_models(self, *, api_key=None, base_url=None, timeout=8.0):
        """Fetch models from KiloCode gateway and filter to :free suffix only."""
        models = super().fetch_models(
            api_key=api_key, base_url=base_url, timeout=timeout
        )
        if models is None:
            return None
        # Filter to only free models (those with :free suffix)
        free_models = [m for m in models if m.endswith(":free")]
        return free_models if free_models else models


kilocode = KiloCodeFreeProvider(name="kilocode")

register_provider(kilocode)
