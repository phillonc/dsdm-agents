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
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
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
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                timeout=int(os.environ.get("GEMINI_TIMEOUT", "120")),
            )

        elif provider == LLMProvider.OLLAMA:
            return cls(
                provider=provider,
                model=os.environ.get("OLLAMA_MODEL", "kimi-k2-thinking:cloud"),
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
            "max_tokens": kwargs.get("max_tokens", 8192),
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

        # Convert messages to OpenAI format, handling complex content structures
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle Anthropic-style tool results (list of tool_result dicts)
            if isinstance(content, list) and content:
                if isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    # OpenAI expects tool messages for tool results
                    for tr in content:
                        tool_call_id = tr.get("tool_use_id", "unknown")
                        result = tr.get("content", "")
                        full_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result,
                        })
                    continue  # Skip normal message append
                elif hasattr(content[0], "text"):
                    # Anthropic raw_content blocks
                    text_parts = []
                    for block in content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
                    content = "\n".join(text_parts)
                else:
                    # Unknown list format - stringify
                    content = str(content)

            full_messages.append({"role": role, "content": content})

        request_params = {
            "model": self.config.model,
            "messages": full_messages,
            "max_tokens": kwargs.get("max_tokens", 8192),
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

    def _convert_protobuf_to_dict(self, obj: Any) -> Any:
        """Convert Protobuf objects to native Python types.

        Handles RepeatedCompositeFieldContainer, MapComposite, Struct, and other
        Protobuf types that can't be directly JSON serialized.
        """
        # Handle None - return empty dict for tool args context
        if obj is None:
            return {}

        # Handle native Python dict (already converted)
        if isinstance(obj, dict):
            return obj

        # Handle basic types
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # Handle google.protobuf.Struct specifically (used by Gemini for function args)
        # Struct has a 'fields' attribute containing the actual key-value pairs
        if hasattr(obj, "fields"):
            result = {}
            try:
                for key, value in obj.fields.items():
                    result[key] = self._convert_protobuf_value(value)
                return result
            except Exception:
                # If fields iteration fails, try MessageToDict
                pass

        # Handle dict-like objects (including MapComposite)
        if hasattr(obj, "keys") and hasattr(obj, "items"):
            try:
                return {k: self._convert_protobuf_to_dict(v) for k, v in obj.items()}
            except Exception:
                pass

        # Handle list-like objects (including RepeatedCompositeFieldContainer)
        if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
            try:
                return [self._convert_protobuf_to_dict(item) for item in obj]
            except Exception:
                pass

        # Handle Protobuf messages with DESCRIPTOR - use preserving_proto_field_name
        # to keep original field names (e.g., "file_path" instead of "filePath")
        if hasattr(obj, "DESCRIPTOR"):
            try:
                from google.protobuf.json_format import MessageToDict
                return MessageToDict(obj, preserving_proto_field_name=True)
            except Exception:
                pass

        # Fallback: return empty dict for tool args (safer than string)
        return {}

    def _convert_protobuf_value(self, value: Any) -> Any:
        """Convert a google.protobuf.Value to a native Python type.

        Protobuf Value can contain: null, number, string, bool, struct, or list.
        """
        # Handle None
        if value is None:
            return None

        # Handle already-converted Python types
        if isinstance(value, (str, int, float, bool, dict, list)):
            return value

        # Try to use WhichOneof to determine the value type (more reliable)
        if hasattr(value, "WhichOneof"):
            try:
                kind = value.WhichOneof("kind")
                if kind == "null_value":
                    return None
                elif kind == "number_value":
                    return value.number_value
                elif kind == "string_value":
                    return value.string_value
                elif kind == "bool_value":
                    return value.bool_value
                elif kind == "struct_value":
                    return self._convert_protobuf_to_dict(value.struct_value)
                elif kind == "list_value":
                    return [self._convert_protobuf_value(v) for v in value.list_value.values]
            except Exception:
                pass

        # Fallback: Check which field is set in the Value using HasField
        try:
            if hasattr(value, "null_value") and value.HasField("null_value"):
                return None
            if hasattr(value, "number_value") and value.HasField("number_value"):
                return value.number_value
            if hasattr(value, "string_value") and value.HasField("string_value"):
                return value.string_value
            if hasattr(value, "bool_value") and value.HasField("bool_value"):
                return value.bool_value
            if hasattr(value, "struct_value") and value.HasField("struct_value"):
                return self._convert_protobuf_to_dict(value.struct_value)
            if hasattr(value, "list_value") and value.HasField("list_value"):
                return [self._convert_protobuf_value(v) for v in value.list_value.values]
        except Exception:
            pass

        # Last resort fallback: try to access value attributes directly
        if hasattr(value, "string_value") and value.string_value:
            return value.string_value
        if hasattr(value, "number_value"):
            try:
                return value.number_value
            except Exception:
                pass

        # Return None for unknown value types
        return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
            from google.ai import generativelanguage as glm
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            )

        # Ensure API key is configured before any operations
        genai.configure(api_key=self.config.api_key)

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]

            # Handle Anthropic-style tool results (list of tool_result dicts)
            if isinstance(content, list) and content and isinstance(content[0], dict):
                if content[0].get("type") == "tool_result":
                    # Convert to Gemini function response format
                    parts = []
                    for tool_result in content:
                        tool_use_id = tool_result.get("tool_use_id", "unknown")
                        # Extract function name from ID format: "gemini_{func_name}_{counter}"
                        # e.g., "gemini_file_write_1" -> "file_write"
                        if tool_use_id.startswith("gemini_"):
                            # Remove "gemini_" prefix and trailing "_N" counter
                            parts_of_id = tool_use_id[7:].rsplit("_", 1)
                            func_name = parts_of_id[0] if parts_of_id else tool_use_id
                        else:
                            func_name = tool_use_id
                        parts.append(glm.Part(
                            function_response=glm.FunctionResponse(
                                name=func_name,
                                response={"result": tool_result.get("content", "")}
                            )
                        ))
                    gemini_messages.append({"role": role, "parts": parts})
                    continue

            # Handle Anthropic raw_content (list of content blocks)
            if isinstance(content, list):
                parts = []
                for block in content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                    elif hasattr(block, "name"):  # Tool use block
                        parts.append(glm.Part(
                            function_call=glm.FunctionCall(
                                name=block.name,
                                args=block.input
                            )
                        ))
                if parts:
                    gemini_messages.append({"role": role, "parts": parts})
                continue

            # Regular text content
            gemini_messages.append({
                "role": role,
                "parts": [content] if isinstance(content, str) else [str(content)]
            })

        # Create chat with system instruction
        generation_config = genai.GenerationConfig(
            max_output_tokens=kwargs.get("max_tokens", 8192),
        )

        # Handle tools if provided - convert to Gemini format
        gemini_tools = None
        if tools:
            gemini_tools = []
            for tool in tools:
                gemini_tools.append(
                    glm.Tool(
                        function_declarations=[
                            glm.FunctionDeclaration(
                                name=tool.get("name"),
                                description=tool.get("description", ""),
                                parameters=self._convert_schema_to_gemini(
                                    tool.get("input_schema", {})
                                ),
                            )
                        ]
                    )
                )

        # Try to add system_instruction if supported (not available in all versions)
        try:
            model = genai.GenerativeModel(
                self.config.model,
                system_instruction=system_prompt if system_prompt else None,
                generation_config=generation_config,
                tools=gemini_tools,
            )
        except TypeError:
            # Fallback for older versions that don't support system_instruction
            model = genai.GenerativeModel(
                self.config.model,
                generation_config=generation_config,
                tools=gemini_tools,
            )
            # Prepend system prompt to first message if we have one
            if system_prompt and gemini_messages:
                first_msg = gemini_messages[0]
                if isinstance(first_msg.get("parts"), list) and first_msg["parts"]:
                    first_content = first_msg["parts"][0]
                    if isinstance(first_content, str):
                        first_msg["parts"][0] = f"System: {system_prompt}\n\nUser: {first_content}"

        chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])

        message_content = gemini_messages[-1]["parts"][0] if gemini_messages else ""

        # Handle StopCandidateException and other errors from Gemini
        try:
            response = chat.send_message(message_content)
        except Exception as e:
            error_type = type(e).__name__
            # Handle StopCandidateException (safety blocks, recitation, etc.)
            if "StopCandidate" in error_type:
                # Try to extract candidate info from the exception
                candidate_info = str(e)
                return {
                    "content": f"Response blocked by Gemini safety filters: {candidate_info}",
                    "role": "assistant",
                    "model": self.config.model,
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "stop_reason": "blocked",
                    "tool_calls": [],
                    "error": error_type,
                }
            # Re-raise other exceptions
            raise

        # Extract tool calls if any
        tool_calls = []
        content = ""
        tool_id_counter = 0
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call:
                tool_id_counter += 1
                func_name = part.function_call.name
                raw_args = part.function_call.args

                # Debug: Log raw args type and value
                import sys
                print(f"[DEBUG] Tool: {func_name}, Raw args type: {type(raw_args).__name__}", file=sys.stderr)

                # Convert Protobuf args to native Python dict
                # This handles RepeatedCompositeFieldContainer and other Protobuf types
                args = self._convert_protobuf_to_dict(raw_args)

                # Debug: Log converted args
                print(f"[DEBUG] Tool: {func_name}, Converted args: {args}", file=sys.stderr)

                tool_calls.append({
                    # Encode function name in ID for proper response mapping
                    "id": f"gemini_{func_name}_{tool_id_counter}",
                    "name": func_name,
                    "input": args if isinstance(args, dict) else {},
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
            from google.ai import generativelanguage as glm
        except ImportError:
            return None

        if not schema:
            return None

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        type_map = {
            "string": glm.Type.STRING,
            "integer": glm.Type.INTEGER,
            "number": glm.Type.NUMBER,
            "boolean": glm.Type.BOOLEAN,
            "array": glm.Type.ARRAY,
            "object": glm.Type.OBJECT,
        }

        gemini_properties = {}
        for name, prop in properties.items():
            prop_type = prop.get("type", "string")
            schema_kwargs = {
                "type_": type_map.get(prop_type, glm.Type.STRING),
                "description": prop.get("description", ""),
            }

            # Handle array items
            if prop_type == "array" and "items" in prop:
                items = prop["items"]
                items_type = items.get("type", "string")
                schema_kwargs["items"] = glm.Schema(
                    type_=type_map.get(items_type, glm.Type.STRING),
                )

            gemini_properties[name] = glm.Schema(**schema_kwargs)

        return glm.Schema(
            type_=glm.Type.OBJECT,
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

        # Convert messages to Ollama format, handling complex content structures
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle Anthropic-style tool results (list of tool_result dicts)
            if isinstance(content, list) and content:
                if isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    # Convert tool results to plain text for Ollama
                    tool_results = []
                    for tr in content:
                        tool_id = tr.get("tool_use_id", "unknown")
                        result = tr.get("content", "")
                        tool_results.append(f"Tool {tool_id} returned: {result}")
                    content = "\n".join(tool_results)
                elif hasattr(content[0], "text"):
                    # Anthropic raw_content blocks
                    text_parts = []
                    for block in content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
                    content = "\n".join(text_parts)
                else:
                    # Unknown list format - stringify
                    content = str(content)

            ollama_messages.append({"role": role, "content": content})

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
