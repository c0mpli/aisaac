"""
Resilient LLM Client — supports 5 backends with agent-specific routing.

Backend 1: ANTHROPIC API (needs ANTHROPIC_API_KEY)
Backend 2: CLAUDE CODE CLI (uses Pro/Max subscription, FREE)
Backend 3: OPENAI-COMPATIBLE PROXY (e.g., CLIProxyAPI)
Backend 4: GEMINI (needs GEMINI_API_KEY) — google-genai package
Backend 5: OPENAI (needs OPENAI_API_KEY) — openai package

Agent routing: each pipeline phase can specify a preferred backend+model.
Fallback chain: if preferred fails, try next available.

Default routing (set via AGENT_ROUTING or override per-call):
  assumption_extraction  → gemini-2.5-flash (cheap, fast)
  contradiction_finding  → gemini-2.5-pro (reasoning)
  convergence            → gemini-2.5-pro
  shared_failure         → gemini-2.5-pro
  obstacle_extraction    → gemini-2.5-flash (cheap, fast)
  reframing              → gpt-4.1 (creative)
  premise_ranking        → no LLM (pure computation)
  extraction             → anthropic (existing default)
  normalization          → anthropic (existing default)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

# Auto-load .env if present
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())
from typing import Optional

from .config import ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS, CACHE_DIR

log = logging.getLogger(__name__)


class Backend:
    API = "api"
    CLAUDE_CODE = "claude_code"
    PROXY = "proxy"
    GEMINI = "gemini"
    OPENAI = "openai"


# Agent routing: phase → (backend, model)
# Override with env var AISAAC_AGENT_ROUTING=phase:backend:model,...
DEFAULT_AGENT_ROUTING = {
    "assumption_extraction": (Backend.GEMINI, "gemini-2.5-flash"),
    "contradiction_finding": (Backend.GEMINI, "gemini-2.5-pro"),
    "convergence": (Backend.GEMINI, "gemini-2.5-pro"),
    "shared_failure": (Backend.GEMINI, "gemini-2.5-pro"),
    "obstacle_extraction": (Backend.GEMINI, "gemini-2.5-flash"),
    "obstacle_universality": (Backend.GEMINI, "gemini-2.5-pro"),
    "reframing": (Backend.OPENAI, "gpt-4.1"),
    "premise_tracing": (Backend.GEMINI, "gemini-2.5-pro"),
    # Existing phases keep Anthropic as default
    "extraction": (Backend.API, ANTHROPIC_MODEL),
    "normalization": (Backend.API, ANTHROPIC_MODEL),
}


def detect_backend() -> str:
    """Detect primary (default) backend."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        log.info("Backend: Anthropic API (ANTHROPIC_API_KEY)")
        return Backend.API
    if shutil.which("claude"):
        log.info("Backend: Claude Code CLI (subscription)")
        return Backend.CLAUDE_CODE
    if os.environ.get("GEMINI_API_KEY"):
        log.info("Backend: Gemini API (GEMINI_API_KEY)")
        return Backend.GEMINI
    if os.environ.get("OPENAI_API_KEY"):
        log.info("Backend: OpenAI API (OPENAI_API_KEY)")
        return Backend.OPENAI
    if os.environ.get("AISAAC_PROXY_URL"):
        log.info(f"Backend: Proxy ({os.environ['AISAAC_PROXY_URL']})")
        return Backend.PROXY
    raise RuntimeError(
        "No LLM backend found. Options:\n"
        "  1. export ANTHROPIC_API_KEY=sk-ant-...   (Anthropic API)\n"
        "  2. export GEMINI_API_KEY=...             (Gemini API)\n"
        "  3. export OPENAI_API_KEY=...             (OpenAI API)\n"
        "  4. npm i -g @anthropic-ai/claude-code && claude login   (subscription, FREE)\n"
        "  5. export AISAAC_PROXY_URL=http://localhost:8317/v1   (proxy)\n"
    )


def _detect_available_backends() -> dict[str, bool]:
    """Check which backends have credentials configured."""
    return {
        Backend.API: bool(os.environ.get("ANTHROPIC_API_KEY")),
        Backend.GEMINI: bool(os.environ.get("GEMINI_API_KEY")),
        Backend.OPENAI: bool(os.environ.get("OPENAI_API_KEY")),
        Backend.CLAUDE_CODE: bool(shutil.which("claude")),
        Backend.PROXY: bool(os.environ.get("AISAAC_PROXY_URL")),
    }


# ── Cache ────────────────────────────────────────────────────────

class ResponseCache:
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = Path(cache_dir or CACHE_DIR) / "llm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _key(self, model: str, temperature: float, messages: list[dict]) -> str:
        content = json.dumps({"model": model, "temp": temperature, "msgs": messages}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, model: str, temperature: float, messages: list[dict]) -> Optional[str]:
        path = self.cache_dir / f"{self._key(model, temperature, messages)}.json"
        if path.exists():
            self.hits += 1
            return json.loads(path.read_text()).get("response_text")
        self.misses += 1
        return None

    def put(self, model: str, temperature: float, messages: list[dict], text: str):
        path = self.cache_dir / f"{self._key(model, temperature, messages)}.json"
        path.write_text(json.dumps({"response_text": text, "ts": time.time()}))


# ── Cost Tracker ─────────────────────────────────────────────────

class CostTracker:
    def __init__(self):
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls_by_phase: dict[str, dict] = {}
        self.backend = "unknown"

    def record(self, phase: str, inp: int = 0, out: int = 0):
        self.total_calls += 1
        self.total_input_tokens += inp
        self.total_output_tokens += out
        self.calls_by_phase.setdefault(phase, {"calls": 0, "input": 0, "output": 0})
        self.calls_by_phase[phase]["calls"] += 1
        self.calls_by_phase[phase]["input"] += inp
        self.calls_by_phase[phase]["output"] += out

    @property
    def estimated_cost(self) -> float:
        if self.backend != Backend.API:
            return 0.0
        return (self.total_input_tokens / 1e6 * 3.0 + self.total_output_tokens / 1e6 * 15.0)

    def summary(self) -> str:
        lines = [f"LLM Usage ({self.backend}): {self.total_calls} calls"]
        if self.backend == Backend.API:
            lines.append(f"  Tokens: {self.total_input_tokens:,} in, {self.total_output_tokens:,} out")
            lines.append(f"  Cost: ~${self.estimated_cost:.2f}")
        else:
            lines.append("  (subscription — no per-token cost)")
        for phase, s in sorted(self.calls_by_phase.items()):
            lines.append(f"  {phase}: {s['calls']} calls")
        return "\n".join(lines)


# ── Backend: Anthropic API ───────────────────────────────────────

class APIBackend:
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(max_retries=0)  # we handle retries ourselves

    def complete(self, messages, model, max_tokens, temperature, system=None):
        kwargs = dict(model=model, max_tokens=max_tokens, temperature=temperature, messages=messages)
        if system:
            kwargs["system"] = system
        resp = self.client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        u = getattr(resp, "usage", None)
        return text, (u.input_tokens if u else 0), (u.output_tokens if u else 0)


# ── Backend: Claude Code CLI ────────────────────────────────────

class ClaudeCodeBackend:
    """
    Calls `claude -p "prompt" --output-format text` as a subprocess.
    Uses your Pro/Max subscription. No API key.
    
    Rate limits are shared with claude.ai web usage.
    Tip: don't use the web app while the pipeline runs.
    """

    def __init__(self):
        self.path = shutil.which("claude")
        if not self.path:
            raise RuntimeError(
                "Claude Code not found.\n"
                "Install: npm install -g @anthropic-ai/claude-code\n"
                "Then: claude login"
            )
        # Verify it works
        try:
            r = subprocess.run([self.path, "--version"], capture_output=True, text=True, timeout=10)
            log.info(f"Claude Code version: {r.stdout.strip()}")
        except Exception:
            pass

    def complete(self, messages, model, max_tokens, temperature, system=None):
        # Build prompt from messages
        parts = []
        if system:
            parts.append(system)
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = "\n".join(p.get("text", "") for p in content if p.get("type") == "text")
            parts.append(content)
        prompt = "\n\n".join(parts)

        # Strip null bytes and other control chars that break subprocess
        prompt = prompt.replace("\x00", "").replace("\r", "")

        # Truncate if excessively long (Claude Code CLI has practical limits)
        max_prompt_chars = 80_000
        if len(prompt) > max_prompt_chars:
            third = max_prompt_chars // 3
            prompt = prompt[:third] + "\n\n[...truncated for length...]\n\n" + prompt[-third:]

        # Write prompt to temp file to avoid OS arg length limits
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        cmd = [
            self.path,
            "-p", prompt,
            "--output-format", "text",
            "--model", model,
        ]

        # For very long prompts, use temp file to avoid arg limits
        if len(prompt) > 100_000:
            cmd = [
                self.path,
                "-p", f"Read the file {prompt_file} and follow the instructions in it.",
                "--output-format", "text",
                "--model", model,
                "--allowedTools", "Read",
            ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code timed out (300s)")
        finally:
            try:
                os.unlink(prompt_file)
            except OSError:
                pass

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "rate" in stderr.lower() or "limit" in stderr.lower() or "usage" in stderr.lower():
                raise RateLimitError(f"Subscription rate limited: {stderr[:200]}")
            raise RuntimeError(f"Claude Code error (exit {result.returncode}): {stderr[:300]}")

        text = result.stdout.strip()
        if not text or text.startswith("Error:"):
            raise RuntimeError(f"Claude Code returned empty/error response: {text[:100]}")

        return text, 0, 0


# ── Backend: OpenAI-compatible Proxy ─────────────────────────────

class ProxyBackend:
    """
    Calls any OpenAI-compatible endpoint.
    Works with CLIProxyAPI, LiteLLM, etc.
    Set AISAAC_PROXY_URL and optionally AISAAC_PROXY_KEY.
    """

    def __init__(self):
        import requests as req
        self.req = req
        self.url = os.environ.get("AISAAC_PROXY_URL", "http://localhost:8317/v1")
        self.key = os.environ.get("AISAAC_PROXY_KEY", "not-needed")

    def complete(self, messages, model, max_tokens, temperature, system=None):
        api_msgs = []
        if system:
            api_msgs.append({"role": "system", "content": system})
        api_msgs.extend(messages)

        resp = self.req.post(
            f"{self.url}/chat/completions",
            json={"model": model, "messages": api_msgs, "max_tokens": max_tokens, "temperature": temperature},
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        u = data.get("usage", {})
        return text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


# ── Backend: Gemini ──────────────────────────────────────────────

class GeminiBackend:
    """Google Gemini via google-genai package."""

    def __init__(self):
        try:
            from google import genai
        except ImportError:
            raise RuntimeError("Install google-genai: uv pip install google-genai")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY environment variable")
        self.client = genai.Client(api_key=api_key)

    def complete(self, messages, model, max_tokens, temperature, system=None):
        from google.genai import types

        # Build contents from messages
        contents = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = "\n".join(p.get("text", "") for p in content if p.get("type") == "text")
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=content)]))

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system

        resp = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        text = resp.text or ""
        usage = getattr(resp, "usage_metadata", None)
        inp = getattr(usage, "prompt_token_count", 0) if usage else 0
        out = getattr(usage, "candidates_token_count", 0) if usage else 0
        return text, inp, out


# ── Backend: OpenAI ──────────────────────────────────────────────

class OpenAIBackend:
    """OpenAI API via openai package."""

    def __init__(self):
        try:
            import openai
        except ImportError:
            raise RuntimeError("Install openai: uv pip install openai")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY environment variable")
        self.client = openai.OpenAI(api_key=api_key)

    def complete(self, messages, model, max_tokens, temperature, system=None):
        api_msgs = []
        if system:
            api_msgs.append({"role": "system", "content": system})
        api_msgs.extend(messages)

        resp = self.client.chat.completions.create(
            model=model,
            messages=api_msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        text = resp.choices[0].message.content or ""
        u = resp.usage
        return text, (u.prompt_tokens if u else 0), (u.completion_tokens if u else 0)


class RateLimitError(Exception):
    pass


# ── Unified Client ───────────────────────────────────────────────

class ResilientClient:
    """
    One client to rule them all. Auto-detects backend.
    Retries on rate limits. Caches responses.
    
    Usage:
        client = get_client()
        text = client.complete(
            messages=[{"role": "user", "content": "Extract formulas..."}],
            phase="extraction",
        )
    """

    def __init__(self, backend: str | None = None, max_retries: int = 8,
                 base_delay: float = 5.0, max_delay: float = 120.0, use_cache: bool = True):
        self.backend_type = backend or detect_backend()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.cache = ResponseCache() if use_cache else None
        self.cost_tracker = CostTracker()
        self.cost_tracker.backend = self.backend_type
        self._available = _detect_available_backends()

        # Initialize primary backend
        self._backend = self._create_backend(self.backend_type)

        # Lazily initialized secondary backends for agent routing
        self._backends: dict[str, object] = {self.backend_type: self._backend}

        # Parse agent routing from env or use defaults
        self._routing = dict(DEFAULT_AGENT_ROUTING)
        env_routing = os.environ.get("AISAAC_AGENT_ROUTING", "")
        if env_routing:
            for entry in env_routing.split(","):
                parts = entry.strip().split(":")
                if len(parts) == 3:
                    self._routing[parts[0]] = (parts[1], parts[2])

    def _create_backend(self, backend_type: str) -> object:
        """Create a backend instance. Returns None if unavailable."""
        try:
            if backend_type == Backend.API:
                return APIBackend()
            elif backend_type == Backend.CLAUDE_CODE:
                return ClaudeCodeBackend()
            elif backend_type == Backend.PROXY:
                return ProxyBackend()
            elif backend_type == Backend.GEMINI:
                return GeminiBackend()
            elif backend_type == Backend.OPENAI:
                return OpenAIBackend()
        except Exception as e:
            log.debug(f"Failed to create {backend_type} backend: {e}")
            return None
        return None

    def _get_backend(self, backend_type: str) -> object | None:
        """Get or lazily create a backend."""
        if backend_type not in self._backends:
            self._backends[backend_type] = self._create_backend(backend_type)
        return self._backends.get(backend_type)

    def _resolve_backend_for_phase(self, phase: str) -> tuple[object, str]:
        """Resolve which backend + model to use for a given phase.

        Returns (backend_instance, model_name).
        Falls back through: preferred → primary → any available.
        """
        # Check if this phase has a routing preference
        if phase in self._routing:
            pref_backend_type, pref_model = self._routing[phase]
            if self._available.get(pref_backend_type):
                backend = self._get_backend(pref_backend_type)
                if backend:
                    return backend, pref_model

        # Fallback to primary backend
        return self._backend, ANTHROPIC_MODEL

    def complete(self, messages: list[dict], model: str | None = None,
                 max_tokens: int | None = None, temperature: float = 0.2,
                 system: str | None = None, phase: str = "unknown") -> str:
        # Resolve backend + model for this phase
        routed_backend, routed_model = self._resolve_backend_for_phase(phase)
        model = model or routed_model
        max_tokens = max_tokens or ANTHROPIC_MAX_TOKENS
        active_backend = routed_backend or self._backend

        if self.cache:
            cached = self.cache.get(model, temperature, messages)
            if cached is not None:
                return cached

        last_err = None
        for attempt in range(self.max_retries):
            try:
                text, inp, out = active_backend.complete(
                    messages, model, max_tokens, temperature, system,
                )
                self.cost_tracker.record(phase, inp, out)
                if self.cache and text:
                    self.cache.put(model, temperature, messages, text)
                return text

            except RateLimitError as e:
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                log.warning(f"Rate limited (attempt {attempt+1}), waiting {delay:.0f}s...")
                if self.backend_type == Backend.CLAUDE_CODE:
                    log.warning("  (Subscription limits shared with claude.ai — close web app)")
                time.sleep(delay)
                last_err = e

            except Exception as e:
                err = str(e).lower()
                if any(w in err for w in ["rate", "limit", "429", "overloaded"]):
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    log.warning(f"Rate/overload error, waiting {delay:.0f}s...")
                    time.sleep(delay)
                    last_err = e
                elif any(w in err for w in ["500", "502", "503"]):
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    log.warning(f"Server error, retrying in {delay:.0f}s...")
                    time.sleep(delay)
                    last_err = e
                else:
                    raise

        raise RuntimeError(f"Failed after {self.max_retries} retries ({self.backend_type}): {last_err}")

    def complete_json(self, messages: list[dict], **kwargs) -> dict | list:
        text = self.complete(messages, **kwargs)
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
        for i, ch in enumerate(text):
            if ch in "[{":
                depth = 0
                for j in range(i, len(text)):
                    if text[j] == ch: depth += 1
                    elif text[j] == ("]" if ch == "[" else "}"): 
                        depth -= 1
                        if depth == 0: return json.loads(text[i:j+1])
                return json.loads(text[i:])
        return json.loads(text)


# ── Singleton ────────────────────────────────────────────────────

_client: Optional[ResilientClient] = None

def get_client(**kwargs) -> ResilientClient:
    global _client
    if _client is None:
        _client = ResilientClient(**kwargs)
    return _client

def reset_client():
    global _client
    _client = None
