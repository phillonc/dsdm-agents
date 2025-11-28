"""LLM Provider Configuration and Factory.

Supports multiple LLM providers: Anthropic, OpenAI, Google Gemini, and Ollama.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    provider: LLMProvider
    api_key: Optional[str] = None
    model: str = ""
    base_url: Optional[str] = None
    timeout: int = 120
    organization_id: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None

    @classmethod
    def from_env(cls, provider: Optional[LLMProvider] = None) -> "LLMConfig":
        """Create LLM configuration from environment variables."""
        # Determine provider from env if not specified
        if provider is None:
            provider_str = os.environ.get("LLM_PROVIDER", "anthropic").lower()
            try:
                provider = LLMProvider(provider_str)
            except ValueError:
                provider = LLMProvider.ANTHROPIC

        if provider == LLMProvider.ANTHROPIC:
            return cls(
                provider=provider,
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                timeout=int(os.environ.get("ANTHROPIC_TIMEOUT", "120")),
            )

        elif provider == LLMProvider.OPENAI:
            return cls(
                provider=provider,
                api_key=os.environ.get("OPENAI_API_KEY"),
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                organization_id=os.environ.get("OPENAI_ORG_ID") or None,
                timeout=int(os.environ.get("OPENAI_TIMEOUT", "120")),
            )

        elif provider == LLMProvider.GEMINI:
            return cls(
                provider=provider,
                api_key=os.environ.get("GEMINI_API_KEY"),
                model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp"),
                timeout=int(os.environ.get("GEMINI_TIMEOUT", "120")),
            )

        elif provider == LLMProvider.OLLAMA:
            return cls(
                provider=provider,
                model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                timeout=int(os.environ.get("OLLAMA_TIMEOUT", "120")),
                extra_params={
                    "code_model": os.environ.get("OLLAMA_CODE_MODEL", "codellama"),
                    "embedding_model": os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
                }
            )

        raise ValueError(f"Unknown provider: {provider}")

    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        if self.provider == LLMProvider.OLLAMA:
            # Ollama doesn't require API key, just needs base URL
            return bool(self.base_url and self.model)
        return bool(self.api_key and self.model)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request to the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        request_params = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if system_prompt:
            request_params["system"] = system_prompt

        if tools:
            request_params["tools"] = tools

        response = self.client.messages.create(**request_params)

        # Extract text content
        text_content = ""
        tool_calls = []
        for block in response.content:
            if hasattr(block, "text"):
                text_content = block.text
            elif hasattr(block, "name"):
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return {
            "content": text_content,
            "role": response.role,
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "stop_reason": response.stop_reason,
            "tool_calls": tool_calls,
            "raw_content": response.content,  # Preserve raw content for agent loop
        }

    def is_available(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False


class OpenAIClient(BaseLLMClient):
    """OpenAI client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    organization=self.config.organization_id,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        # Prepend system message if provided
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        request_params = {
            "model": self.config.model,
            "messages": full_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if tools:
            # Convert to OpenAI tool format
            request_params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    }
                }
                for tool in tools
            ]

        response = self.client.chat.completions.create(**request_params)
        message = response.choices[0].message

        tool_calls = []
        if message.tool_calls:
            import json
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments) if tc.function.arguments else {},
                })

        return {
            "content": message.content or "",
            "role": message.role,
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            "stop_reason": response.choices[0].finish_reason,
            "tool_calls": tool_calls,
            "raw_tool_calls": message.tool_calls,  # Preserve for agent loop
        }

    def is_available(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False


class GeminiClient(BaseLLMClient):
    """Google Gemini client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise ImportError(
                    "google-generativeai package not installed. "
                    "Run: pip install google-generativeai"
                )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [msg["content"]]
            })

        # Create chat with system instruction
        generation_config = genai.GenerationConfig(
            max_output_tokens=kwargs.get("max_tokens", 4096),
        )

        model = genai.GenerativeModel(
            self.config.model,
            system_instruction=system_prompt if system_prompt else None,
            generation_config=generation_config,
        )

        # Handle tools if provided
        gemini_tools = None
        if tools:
            gemini_tools = []
            for tool in tools:
                gemini_tools.append(
                    genai.protos.Tool(
                        function_declarations=[
                            genai.protos.FunctionDeclaration(
                                name=tool.get("name"),
                                description=tool.get("description", ""),
                                parameters=self._convert_schema_to_gemini(
                                    tool.get("input_schema", {})
                                ),
                            )
                        ]
                    )
                )

        chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
        response = chat.send_message(
            gemini_messages[-1]["parts"][0] if gemini_messages else "",
            tools=gemini_tools,
        )

        # Extract tool calls if any
        tool_calls = []
        content = ""
        tool_id_counter = 0
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call:
                tool_id_counter += 1
                tool_calls.append({
                    "id": f"gemini_tool_{tool_id_counter}",
                    "name": part.function_call.name,
                    "input": dict(part.function_call.args),
                })
            elif hasattr(part, "text"):
                content += part.text

        return {
            "content": content,
            "role": "assistant",
            "model": self.config.model,
            "usage": {
                "input_tokens": response.usage_metadata.prompt_token_count if hasattr(response, "usage_metadata") else 0,
                "output_tokens": response.usage_metadata.candidates_token_count if hasattr(response, "usage_metadata") else 0,
            },
            "stop_reason": "tool_use" if tool_calls else "stop",
            "tool_calls": tool_calls,
        }

    def _convert_schema_to_gemini(self, schema: Dict[str, Any]) -> Any:
        """Convert JSON schema to Gemini parameter format."""
        try:
            import google.generativeai as genai
        except ImportError:
            return None

        if not schema:
            return None

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        gemini_properties = {}
        for name, prop in properties.items():
            prop_type = prop.get("type", "string")
            type_map = {
                "string": genai.protos.Type.STRING,
                "integer": genai.protos.Type.INTEGER,
                "number": genai.protos.Type.NUMBER,
                "boolean": genai.protos.Type.BOOLEAN,
                "array": genai.protos.Type.ARRAY,
                "object": genai.protos.Type.OBJECT,
            }
            gemini_properties[name] = genai.protos.Schema(
                type=type_map.get(prop_type, genai.protos.Type.STRING),
                description=prop.get("description", ""),
            )

        return genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties=gemini_properties,
            required=required,
        )

    def is_available(self) -> bool:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            models = genai.list_models()
            return any(True for _ in models)
        except Exception:
            return False


class OllamaClient(BaseLLMClient):
    """Ollama local LLM client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._session = None

    @property
    def session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.timeout = self.config.timeout
        return self._session

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        url = f"{self.config.base_url}/api/chat"

        # Build messages with system prompt
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(messages)

        request_data = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": False,
        }

        # Ollama supports tools in newer versions
        if tools:
            request_data["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    }
                }
                for tool in tools
            ]

        response = self.session.post(url, json=request_data)
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        tool_calls = []

        if message.get("tool_calls"):
            for idx, tc in enumerate(message["tool_calls"]):
                tool_calls.append({
                    "id": f"ollama_tool_{idx + 1}",
                    "name": tc.get("function", {}).get("name", ""),
                    "input": tc.get("function", {}).get("arguments", {}),
                })

        return {
            "content": message.get("content", ""),
            "role": message.get("role", "assistant"),
            "model": data.get("model", self.config.model),
            "usage": {
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            "stop_reason": "tool_use" if tool_calls else ("stop" if data.get("done") else "length"),
            "tool_calls": tool_calls,
        }

    def is_available(self) -> bool:
        try:
            response = self.session.get(f"{self.config.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False


def create_llm_client(
    provider: Optional[LLMProvider] = None,
    config: Optional[LLMConfig] = None,
) -> BaseLLMClient:
    """Factory function to create an LLM client.

    Args:
        provider: The LLM provider to use. If None, reads from LLM_PROVIDER env var.
        config: Optional pre-built configuration. If None, reads from environment.

    Returns:
        An LLM client instance for the specified provider.

    Raises:
        ValueError: If the provider is unknown or not configured.
    """
    if config is None:
        config = LLMConfig.from_env(provider)

    if not config.is_configured():
        raise ValueError(
            f"Provider {config.provider.value} is not properly configured. "
            f"Please check your environment variables."
        )

    client_map = {
        LLMProvider.ANTHROPIC: AnthropicClient,
        LLMProvider.OPENAI: OpenAIClient,
        LLMProvider.GEMINI: GeminiClient,
        LLMProvider.OLLAMA: OllamaClient,
    }

    client_class = client_map.get(config.provider)
    if client_class is None:
        raise ValueError(f"Unknown provider: {config.provider}")

    return client_class(config)


def get_available_providers() -> List[LLMProvider]:
    """Get a list of all configured and available providers."""
    available = []
    for provider in LLMProvider:
        try:
            config = LLMConfig.from_env(provider)
            if config.is_configured():
                client = create_llm_client(config=config)
                if client.is_available():
                    available.append(provider)
        except Exception:
            continue
    return available


def get_default_provider() -> LLMProvider:
    """Get the default provider from environment or return Anthropic."""
    provider_str = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    try:
        return LLMProvider(provider_str)
    except ValueError:
        return LLMProvider.ANTHROPIC
