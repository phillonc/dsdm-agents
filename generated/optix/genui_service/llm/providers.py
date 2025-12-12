"""
LLM Provider Abstraction Layer

Supports multiple LLM providers (Anthropic, Google, OpenAI) with
a unified interface for UI code generation.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from ..config import settings


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: str
    model: str
    token_count: int
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.default_llm_model
        self._client = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate using Claude."""
        client = await self._get_client()

        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        response = await client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            provider=self.provider_name,
            model=self.model,
            token_count=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason or "stop",
        )


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.google_api_key
        self.model = model or "gemini-2.5-pro"
        self._client = None

    @property
    def provider_name(self) -> str:
        return "google"

    async def _get_client(self):
        """Get or create the Google client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate using Gemini."""
        client = await self._get_client()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }

        if stop_sequences:
            generation_config["stop_sequences"] = stop_sequences

        response = await client.generate_content_async(
            full_prompt,
            generation_config=generation_config,
        )

        # Estimate token count (Gemini doesn't always return this)
        token_estimate = len(prompt.split()) + len(response.text.split())

        return LLMResponse(
            content=response.text,
            provider=self.provider_name,
            model=self.model,
            token_count=token_estimate,
            finish_reason="stop",
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or "gpt-4o"
        self._client = None

    @property
    def provider_name(self) -> str:
        return "openai"

    async def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate using GPT."""
        client = await self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if stop_sequences:
            kwargs["stop"] = stop_sequences

        response = await client.chat.completions.create(**kwargs)

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider_name,
            model=self.model,
            token_count=response.usage.total_tokens,
            finish_reason=response.choices[0].finish_reason,
        )


class MockProvider(LLMProvider):
    """Mock provider for testing without API calls."""

    def __init__(self):
        self.model = "mock-model"

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Generate a mock response."""
        # Generate a basic HTML structure for testing
        mock_html = self._generate_mock_html(prompt)

        return LLMResponse(
            content=mock_html,
            provider=self.provider_name,
            model=self.model,
            token_count=len(mock_html.split()),
            finish_reason="stop",
        )

    def _generate_mock_html(self, prompt: str) -> str:
        """Generate mock HTML based on prompt content."""
        prompt_lower = prompt.lower()

        # Detect what kind of UI to generate
        if "options" in prompt_lower and "chain" in prompt_lower:
            return self._mock_options_chain()
        elif "quote" in prompt_lower or "price" in prompt_lower:
            return self._mock_quote_card()
        elif "greeks" in prompt_lower:
            return self._mock_greeks_display()
        elif "payoff" in prompt_lower or "p&l" in prompt_lower:
            return self._mock_payoff_diagram()
        else:
            return self._mock_generic_card()

    def _mock_options_chain(self) -> str:
        return '''```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Options Chain</title>
  <style>
    :root {
      --optix-primary: #2563EB;
      --optix-bg-dark: #0F172A;
      --optix-text: #F1F5F9;
      --optix-green: #22C55E;
      --optix-red: #EF4444;
    }
    body { font-family: Inter, sans-serif; background: var(--optix-bg-dark); color: var(--optix-text); margin: 0; padding: 16px; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .symbol { font-size: 24px; font-weight: 700; }
    .price { font-size: 20px; color: var(--optix-green); }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 12px 8px; text-align: right; border-bottom: 1px solid #334155; }
    th { background: #1E293B; position: sticky; top: 0; }
    .strike { text-align: center; font-weight: 600; background: #1E293B; }
    .loading { opacity: 0.5; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <span class="symbol" data-bind="symbol">AAPL</span>
      <span class="price" data-bind="price">$185.50</span>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Bid</th><th>Ask</th><th>Vol</th><th>OI</th><th>Δ</th>
        <th class="strike">Strike</th>
        <th>Δ</th><th>OI</th><th>Vol</th><th>Ask</th><th>Bid</th>
      </tr>
    </thead>
    <tbody id="chain-body">
      <tr>
        <td>3.50</td><td>3.55</td><td>1.2K</td><td>5.6K</td><td>0.52</td>
        <td class="strike">185</td>
        <td>-0.48</td><td>4.2K</td><td>890</td><td>2.85</td><td>2.80</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
```'''

    def _mock_quote_card(self) -> str:
        return '''```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Quote Card</title>
  <style>
    :root { --optix-primary: #2563EB; --optix-bg-dark: #0F172A; --optix-text: #F1F5F9; --optix-green: #22C55E; }
    body { font-family: Inter, sans-serif; background: var(--optix-bg-dark); color: var(--optix-text); margin: 0; padding: 16px; }
    .card { background: #1E293B; border-radius: 12px; padding: 20px; }
    .symbol { font-size: 28px; font-weight: 700; }
    .price { font-size: 36px; color: var(--optix-green); margin: 8px 0; }
    .change { color: var(--optix-green); }
  </style>
</head>
<body>
  <div class="card">
    <div class="symbol" data-bind="symbol">AAPL</div>
    <div class="price" data-bind="price">$185.50</div>
    <div class="change">+$1.25 (+0.68%)</div>
  </div>
</body>
</html>
```'''

    def _mock_greeks_display(self) -> str:
        return '''```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Greeks Display</title>
  <style>
    :root { --optix-primary: #2563EB; --optix-bg-dark: #0F172A; --optix-text: #F1F5F9; }
    body { font-family: Inter, sans-serif; background: var(--optix-bg-dark); color: var(--optix-text); margin: 0; padding: 16px; }
    .greeks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
    .greek-card { background: #1E293B; border-radius: 8px; padding: 16px; text-align: center; }
    .greek-label { color: #94A3B8; font-size: 12px; text-transform: uppercase; }
    .greek-value { font-size: 24px; font-weight: 600; margin-top: 4px; }
  </style>
</head>
<body>
  <div class="greeks-grid">
    <div class="greek-card"><div class="greek-label">Delta</div><div class="greek-value">0.52</div></div>
    <div class="greek-card"><div class="greek-label">Gamma</div><div class="greek-value">0.03</div></div>
    <div class="greek-card"><div class="greek-label">Theta</div><div class="greek-value">-0.08</div></div>
    <div class="greek-card"><div class="greek-label">Vega</div><div class="greek-value">0.25</div></div>
  </div>
</body>
</html>
```'''

    def _mock_payoff_diagram(self) -> str:
        return '''```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Payoff Diagram</title>
  <style>
    :root { --optix-primary: #2563EB; --optix-bg-dark: #0F172A; --optix-text: #F1F5F9; --optix-green: #22C55E; --optix-red: #EF4444; }
    body { font-family: Inter, sans-serif; background: var(--optix-bg-dark); color: var(--optix-text); margin: 0; padding: 16px; }
    .chart-container { background: #1E293B; border-radius: 12px; padding: 20px; height: 300px; display: flex; align-items: center; justify-content: center; }
    .stats { display: flex; gap: 24px; margin-top: 16px; }
    .stat { text-align: center; }
    .stat-label { color: #94A3B8; font-size: 12px; }
    .stat-value { font-size: 18px; font-weight: 600; }
    .profit { color: var(--optix-green); }
    .loss { color: var(--optix-red); }
  </style>
</head>
<body>
  <div class="chart-container">
    <canvas id="payoffChart">[Payoff Chart]</canvas>
  </div>
  <div class="stats">
    <div class="stat"><div class="stat-label">Max Profit</div><div class="stat-value profit">$500</div></div>
    <div class="stat"><div class="stat-label">Max Loss</div><div class="stat-value loss">-$200</div></div>
    <div class="stat"><div class="stat-label">Breakeven</div><div class="stat-value">$187.50</div></div>
  </div>
</body>
</html>
```'''

    def _mock_generic_card(self) -> str:
        return '''```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OPTIX</title>
  <style>
    :root { --optix-primary: #2563EB; --optix-bg-dark: #0F172A; --optix-text: #F1F5F9; }
    body { font-family: Inter, sans-serif; background: var(--optix-bg-dark); color: var(--optix-text); margin: 0; padding: 16px; }
    .card { background: #1E293B; border-radius: 12px; padding: 20px; }
    h1 { margin: 0 0 16px; }
    p { color: #94A3B8; margin: 0; }
  </style>
</head>
<body>
  <div class="card">
    <h1>OPTIX</h1>
    <p>Generated UI content will appear here.</p>
  </div>
</body>
</html>
```'''


async def get_llm_provider(
    provider: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider: Provider name (anthropic, google, openai, mock)
        **kwargs: Additional provider-specific arguments

    Returns:
        LLMProvider instance
    """
    provider = provider or settings.default_llm_provider

    if provider == "anthropic":
        api_key = kwargs.get("api_key") or settings.anthropic_api_key
        if not api_key:
            # Fall back to mock if no API key
            return MockProvider()
        return AnthropicProvider(api_key=api_key, **kwargs)

    elif provider == "google":
        api_key = kwargs.get("api_key") or settings.google_api_key
        if not api_key:
            return MockProvider()
        return GoogleProvider(api_key=api_key, **kwargs)

    elif provider == "openai":
        api_key = kwargs.get("api_key") or settings.openai_api_key
        if not api_key:
            return MockProvider()
        return OpenAIProvider(api_key=api_key, **kwargs)

    elif provider == "mock":
        return MockProvider()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
