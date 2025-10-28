from ..config import settings
from ..providers import MQTTProvider, OpenAIProvider, OllamaProvider, LLMProvider


_provider_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "mqtt":
        _provider_instance = MQTTProvider()
    elif provider == "openai":
        _provider_instance = OpenAIProvider()
    elif provider == "ollama":
        _provider_instance = OllamaProvider()
    else:
        _provider_instance = MQTTProvider()
    return _provider_instance


