"""Chat-model factory. Provider is chosen via MAESTRO_LLM_PROVIDER."""

from .config import settings


def _model(provider: str, model_name: str, temperature: float = 0.0):
    """Lazily import the provider client so an unused provider's package isn't required."""
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, temperature=temperature)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, temperature=temperature)
    if provider == "bedrock":
        from langchain_aws.chat_models.bedrock import ChatBedrock

        return ChatBedrock(model_id=model_name, temperature=temperature)
    raise ValueError(f"Unknown LLM provider: {provider!r}")


def router_model():
    """Cheap model used for request routing and simple direct answers."""
    return _model(settings.llm_provider, settings.router_model)


def agent_model():
    """Strong model used for tool-use reasoning."""
    return _model(settings.llm_provider, settings.agent_model)
