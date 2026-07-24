"""
title: DevSecOps Agent Pipeline
author: AI-Content Team
version: 1.0.0
description: >
    An agentic pipeline that connects to an MCP Gateway via HTTP
    and uses IBM ICA as the LLM backend. The agent discovers tools
    from the MCP gateway, sends them to the LLM, and executes
    tool calls in a loop until a final answer is produced.
required_open_webui_version: 0.4.0
requirements: requests, urllib3
"""

import json
import os
import re
import time
import uuid
import logging
import traceback
from typing import (
    Any,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Union,
)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import BaseModel, Field


# ────────────────────────────────────────────
# Pipeline class
# ────────────────────────────────────────────
class Pipeline:
    """Open WebUI Pipeline that acts as an MCP-aware agent."""

    # ── Configurable settings (editable in the UI) ──
    class Valves(BaseModel):
        # LLM Provider
        PROVIDER_API_BASE: str = Field(
            default="",
            description="LLM API base URL (e.g. https://sg.ica.ibm.com/ica/apis/v3)",
        )
        PROVIDER_API_KEY: str = Field(
            default="",
            description="LLM API key / Bearer token",
        )
        PROVIDER_MODEL_ID: str = Field(
            default="global/anthropic.claude-sonnet-4-6",
            description="Model ID to use for chat completions",
        )
        PROVIDER_MAX_TOKENS: int = Field(
            default=4096,
            description="Max tokens for LLM response",
        )
        PROVIDER_TEMPERATURE: float = Field(
            default=0.2,
            description="Temperature for LLM sampling",
        )

        # MCP Gateway
        MCP_GATEWAY_URL: str = Field(
            default="",
            description="MCP Gateway URL (HTTP Streamable endpoint)",
        )
        MCP_LITELLM_API_KEY: str = Field(
            default="",
            description="x-litellm-api-key header value",
        )
        MCP_DD_API_KEY: str = Field(
            default="",
            description="X-DD-API-KEY header value",
        )
        MCP_HARBOR_URL: str = Field(
            default="",
            description="x-harbor-url header value",
        )
        MCP_HARBOR_USERNAME: str = Field(
            default="",
            description="x-harbor-username header value",
        )
        MCP_HARBOR_PASSWORD: str = Field(
            default="",
            description="x-harbor-password header value",
        )
        MCP_GITLAB_TOKEN: str = Field(
            default="",
            description="Private-Token header value for GitLab",
        )
        MCP_JENKINS_URL: str = Field(
            default="",
            description="x-jenkins-url header value",
        )
        MCP_JENKINS_USERNAME: str = Field(
            default="",
            description="x-jenkins-username header value",
        )
        MCP_JENKINS_PASSWORD: str = Field(
            default="",
            description="x-jenkins-password header value",
        )

        # Agent behaviour
        MAX_AGENT_ITERATIONS: int = Field(
            default=10,
            description="Maximum tool-call iterations before forcing a final answer",
        )
        AGENTS_DIR: str = Field(
            default="agents",
            description="Path to directory containing .agent.md files (e.g. agents or .github/agents)",
        )
    class UserValves(BaseModel):
        PROVIDER_API_KEY: str = Field(
            default="",
            description="Your personal Provider API Key (Bearer token)",
        )

    # ────────────────────────────────────────
    def __init__(self):
        self.name = "DevSecOps agent"
        self.user_valves = self.UserValves()
        self.valves = self.Valves(
            **{
                "PROVIDER_API_BASE": os.getenv(
                    "PROVIDER_API_BASE",
                    "https://sg.ica.ibm.com/ica/apis/v3",
                ),
                "PROVIDER_API_KEY": os.getenv("PROVIDER_API_KEY", ""),
                "PROVIDER_MODEL_ID": os.getenv("PROVIDER_MODEL_ID", "global/anthropic.claude-sonnet-4-6"),
                "AGENTS_DIR": os.getenv("AGENTS_DIR", "agents"),
                "MCP_GATEWAY_URL": os.getenv(
                    "MCP_GATEWAY_URL",
                    "http://ai-gateway.vayu.devopsnonprd.vayuktbcs/mcp",
                ),
                "MCP_LITELLM_API_KEY": os.getenv(
                    "MCP_LITELLM_API_KEY", ""
                ),
                "MCP_DD_API_KEY": os.getenv("MCP_DD_API_KEY", ""),
                "MCP_HARBOR_URL": os.getenv("MCP_HARBOR_URL", ""),
                "MCP_HARBOR_USERNAME": os.getenv("MCP_HARBOR_USERNAME", ""),
                "MCP_HARBOR_PASSWORD": os.getenv("MCP_HARBOR_PASSWORD", ""),
                "MCP_GITLAB_TOKEN": os.getenv("MCP_GITLAB_TOKEN", ""),
                "MCP_JENKINS_URL": os.getenv("MCP_JENKINS_URL", ""),
                "MCP_JENKINS_USERNAME": os.getenv("MCP_JENKINS_USERNAME", ""),
                "MCP_JENKINS_PASSWORD": os.getenv("MCP_JENKINS_PASSWORD", ""),
            }
        )
        self._mcp_tools: List[Dict[str, Any]] = []
        self._mcp_session_id: Optional[str] = None

    # ────────────────────────────────────────
    # Lifecycle hooks
    # ────────────────────────────────────────
    async def on_startup(self):
        print(f"[DevSecOps Agent] Starting up …")
        self._discover_tools()

    async def on_shutdown(self):
        print(f"[DevSecOps Agent] Shutting down …")

    async def on_valves_updated(self):
        print(f"[DevSecOps Agent] Valves updated – re-discovering MCP tools …")
        self._discover_tools()

    # ────────────────────────────────────────
    # MCP helpers
    # ────────────────────────────────────────
    def _mcp_headers(self) -> Dict[str, str]:
        """Build the headers required by the MCP gateway."""
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        v = self.valves
        if v.MCP_LITELLM_API_KEY:
            headers["x-litellm-api-key"] = v.MCP_LITELLM_API_KEY
        if v.MCP_DD_API_KEY:
            headers["X-DD-API-KEY"] = v.MCP_DD_API_KEY
        if v.MCP_HARBOR_URL:
            headers["x-harbor-url"] = v.MCP_HARBOR_URL
        if v.MCP_HARBOR_USERNAME:
            headers["x-harbor-username"] = v.MCP_HARBOR_USERNAME
        if v.MCP_HARBOR_PASSWORD:
            headers["x-harbor-password"] = v.MCP_HARBOR_PASSWORD
        if v.MCP_GITLAB_TOKEN:
            headers["Private-Token"] = v.MCP_GITLAB_TOKEN
        if v.MCP_JENKINS_URL:
            headers["x-jenkins-url"] = v.MCP_JENKINS_URL
        if v.MCP_JENKINS_USERNAME:
            headers["x-jenkins-username"] = v.MCP_JENKINS_USERNAME
        if v.MCP_JENKINS_PASSWORD:
            headers["x-jenkins-password"] = v.MCP_JENKINS_PASSWORD
        return headers

    def _mcp_rpc(self, method: str, params: Optional[dict] = None) -> Any:
        """Send a JSON-RPC 2.0 request to the MCP gateway.

        Handles both regular JSON responses and SSE streaming responses
        from the MCP Streamable HTTP transport.
        """
        rpc_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
        }
        if params:
            payload["params"] = params

        headers = self._mcp_headers()
        if self._mcp_session_id:
            headers["Mcp-Session-Id"] = self._mcp_session_id

        url = self.valves.MCP_GATEWAY_URL
        print(f"[DevSecOps Agent] → {method}  {url}")

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[DevSecOps Agent] MCP request failed: {exc}")
            return None

        # Capture session id from response headers
        session_id = resp.headers.get("Mcp-Session-Id")
        if session_id:
            self._mcp_session_id = session_id

        content_type = resp.headers.get("Content-Type", "")

        # Handle SSE responses
        if "text/event-stream" in content_type:
            return self._parse_sse_response(resp.text, rpc_id)

        # Regular JSON response
        try:
            data = resp.json()
        except Exception:
            print(f"[DevSecOps Agent] Failed to parse MCP response as JSON")
            return None

        # Handle JSON-RPC response
        if isinstance(data, dict):
            if "error" in data:
                print(f"[DevSecOps Agent] MCP error: {data['error']}")
                return None
            return data.get("result")

        # Handle batch responses
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id") == rpc_id:
                    return item.get("result")

        return data

    def _parse_sse_response(self, text: str, rpc_id: str) -> Any:
        """Parse SSE text to extract JSON-RPC result."""
        result = None
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if not data_str:
                    continue
                try:
                    data = json.loads(data_str)
                    if isinstance(data, dict):
                        if "result" in data:
                            result = data["result"]
                        elif "error" in data:
                            print(f"[DevSecOps Agent] MCP SSE error: {data['error']}")
                except json.JSONDecodeError:
                    continue
        return result

    def _discover_tools(self):
        """Call tools/list on the MCP gateway and cache the results."""
        self._mcp_tools = []

        # First initialize the session
        init_result = self._mcp_rpc("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "open-webui-mcp-agent",
                "version": "1.0.0",
            },
        })

        if init_result:
            print(f"[DevSecOps Agent] MCP session initialized")
            # Send initialized notification
            self._send_notification("notifications/initialized")

        # List tools
        result = self._mcp_rpc("tools/list")
        if result and "tools" in result:
            self._mcp_tools = result["tools"]
            tool_names = [t.get("name", "?") for t in self._mcp_tools]
            print(f"[DevSecOps Agent] Discovered {len(self._mcp_tools)} MCP tools: {tool_names}")
        else:
            print("[DevSecOps Agent] No tools discovered from MCP gateway (will retry on next request)")

    def _send_notification(self, method: str, params: Optional[dict] = None):
        """Send a JSON-RPC notification (no id, no response expected)."""
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            payload["params"] = params

        headers = self._mcp_headers()
        if self._mcp_session_id:
            headers["Mcp-Session-Id"] = self._mcp_session_id

        try:
            requests.post(
                self.valves.MCP_GATEWAY_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )
        except requests.RequestException:
            pass  # Notifications are fire-and-forget

    def _call_mcp_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool via MCP gateway and return the result as text."""
        result = self._mcp_rpc("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        if result is None:
            return f"[Error] MCP tool '{name}' returned no result."

        # MCP tool results have a "content" array
        if isinstance(result, dict) and "content" in result:
            parts = []
            for item in result["content"]:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif item.get("type") == "image":
                        parts.append(f"[Image: {item.get('mimeType', 'image')}]")
                    else:
                        parts.append(json.dumps(item, ensure_ascii=False))
                else:
                    parts.append(str(item))
            return "\n".join(parts) if parts else str(result)

    def _mcp_tools_as_text_description(self) -> str:
        """Format MCP tools as a readable text description for the prompt."""
        if not self._mcp_tools:
            return "No tools available."

        lines = []
        for t in self._mcp_tools:
            name = t.get("name", "unknown")
            desc = t.get("description", "No description provided.")
            schema = t.get("inputSchema", {})
            lines.append(f"- **{name}**: {desc}")
            lines.append(f"  Arguments schema: {json.dumps(schema, ensure_ascii=False)}")
        return "\n".join(lines)

    def _mcp_tools_as_openai_functions(self) -> List[Dict[str, Any]]:
        """Convert MCP tool definitions to OpenAI-compatible tool format."""
        tools = []
        for t in self._mcp_tools:
            tool_def: Dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": t.get("name", "unknown"),
                    "description": t.get("description", ""),
                },
            }
            # MCP uses "inputSchema", OpenAI uses "parameters"
            schema = t.get("inputSchema", {})
            if schema:
                tool_def["function"]["parameters"] = schema
            else:
                tool_def["function"]["parameters"] = {
                    "type": "object",
                    "properties": {},
                }
            tools.append(tool_def)
        return tools

    # ────────────────────────────────────────
    # Agent Markdown Loader & Orchestration
    # ────────────────────────────────────────
    def _parse_agent_md(self, file_path: str) -> Dict[str, Any]:
        """Parse a .agent.md file into frontmatter metadata dict and body text."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            print(f"[DevSecOps Agent] Failed to read agent file {file_path}: {exc}")
            return {}

        metadata: Dict[str, Any] = {"file_path": file_path, "name": os.path.basename(file_path)}
        body = content.strip()

        # Split YAML frontmatter demarcated by `---`
        parts = re.split(r"^---\s*$", content, flags=re.MULTILINE)
        if len(parts) >= 3:
            frontmatter_str = parts[1]
            body = "---".join(parts[2:]).strip()
            for line in frontmatter_str.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if val.startswith("[") and val.endswith("]"):
                        items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                        metadata[key] = items
                    elif val.lower() == "true":
                        metadata[key] = True
                    elif val.lower() == "false":
                        metadata[key] = False
                    else:
                        metadata[key] = val

        metadata["body"] = body
        return metadata

    def _load_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Load all .agent.md files from AGENTS_DIR directory."""
        agents_dir = self.valves.AGENTS_DIR
        base_dir = os.path.dirname(os.path.dirname(__file__))
        search_paths = [
            agents_dir,
            os.path.join(base_dir, agents_dir),
            "agents",
            os.path.join(base_dir, "agents"),
            ".github/agents",
            os.path.join(base_dir, ".github/agents"),
        ]

        target_dir = None
        for p in search_paths:
            if os.path.isdir(p):
                target_dir = p
                break

        if not target_dir:
            print(f"[DevSecOps Agent] Warning: AGENTS_DIR '{agents_dir}' not found.")
            return {}

        agents_data: Dict[str, Dict[str, Any]] = {}
        for fname in sorted(os.listdir(target_dir)):
            if fname.endswith(".agent.md") or fname.endswith(".md"):
                file_path = os.path.join(target_dir, fname)
                parsed = self._parse_agent_md(file_path)
                name = parsed.get("name") or fname.replace(".agent.md", "").replace(".md", "")
                agents_data[name] = parsed

        print(f"[DevSecOps Agent] Loaded {len(agents_data)} agents from {target_dir}: {list(agents_data.keys())}")
        return agents_data

    def _build_system_prompt(self) -> str:
        """Build dynamic system prompt using devsecops orchestrator & sub-agents instructions."""
        agents = self._load_all_agents()
        orchestrator = agents.get("devsecops", {})
        orchestrator_body = orchestrator.get("body", "")

        sub_agents_prompts = []
        for name, data in agents.items():
            if name == "devsecops":
                continue
            desc = data.get("description", "")
            body = data.get("body", "")
            sub_agents_prompts.append(
                f"### Sub-Agent: `{name}`\n"
                f"**Description:** {desc}\n\n"
                f"**Detailed Instructions & Workflow:**\n{body}\n"
            )

        sub_agents_text = "\n---\n".join(sub_agents_prompts) if sub_agents_prompts else "No sub-agents available."
        tools_desc = self._mcp_tools_as_text_description()

        header = (
            "You are DevSecOps agent, the Lead Orchestration assistant for SDLC automation and security operations.\n"
            "You automatically route user requests to specialized sub-agent workflows and execute tool calls using MCP tools.\n"
        )

        if orchestrator_body:
            orchestration_instructions = f"## Lead Orchestrator Directive (`devsecops.agent.md`)\n\n{orchestrator_body}\n"
        else:
            orchestration_instructions = (
                "## Lead Orchestrator Directive\n"
                "1. Understand user intent.\n"
                "2. Delegate to the matching sub-agent (dockerfile, defect-fixing, migration).\n"
                "3. Follow the selected sub-agent's step-by-step workflow.\n"
            )

        system_prompt = (
            f"{header}\n"
            f"{orchestration_instructions}\n"
            "==================================================\n"
            "## AVAILABLE SUB-AGENTS & SPECIALIZED WORKFLOWS\n"
            "==================================================\n\n"
            f"{sub_agents_text}\n\n"
            "==================================================\n"
            "## AVAILABLE MCP TOOLS\n"
            "==================================================\n\n"
            f"{tools_desc}\n\n"
            "==================================================\n"
            "## TOOL CALL FORMAT & INSTRUCTIONS\n"
            "==================================================\n"
            "To call a tool, you MUST respond ONLY with a JSON code block in the following format:\n"
            "```json\n"
            "{\n"
            '  "tool": "tool_name",\n'
            '  "arguments": {\n'
            '    "param_name": "param_value"\n'
            "  }\n"
            "}\n"
            "```\n"
            "Do not add any other text before or after the JSON block when calling a tool. "
            "Only call one tool at a time.\n\n"
            "Once you receive the tool result, you can make another tool call or provide your final answer.\n"
            "When you have the final answer, output it normally as regular markdown text.\n"
        )
        return system_prompt

    # ────────────────────────────────────────
    # LLM helpers
    # ────────────────────────────────────────
    def _get_provider_session(self) -> requests.Session:
        """Return a requests Session with retry/backoff for LLM provider."""
        if not hasattr(self, "_provider_session") or self._provider_session is None:
            session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(
                max_retries=retries,
                pool_connections=5,
                pool_maxsize=5,
            )
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            self._provider_session = session
        return self._provider_session

    def _provider_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a chat-completion request to LLM provider API.

        Returns the parsed JSON dict directly (not a Response object).
        Handles TransferEncodingError by reading raw content bytes
        before parsing, and retries on transient failures.
        """
        v = self.valves
        url = f"{v.PROVIDER_API_BASE.rstrip('/')}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or v.PROVIDER_API_KEY}",
            "Accept": "application/json",
            "Connection": "keep-alive",
        }

        payload: Dict[str, Any] = {
            "model": v.PROVIDER_MODEL_ID,
            "messages": messages,
            "max_tokens": v.PROVIDER_MAX_TOKENS,
            "temperature": v.PROVIDER_TEMPERATURE,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        last_exc: Optional[Exception] = None
        session = self._get_provider_session()

        for attempt in range(3):
            try:
                resp = session.post(
                    url,
                    json=payload,
                    headers=headers,
                    stream=False,  # Always read full body to avoid chunked errors
                    timeout=(10, 120),  # (connect_timeout, read_timeout)
                )
                resp.raise_for_status()

                # Read raw bytes first to avoid TransferEncodingError
                # that occurs when .json() iterates over chunks
                raw_bytes = resp.content  # reads entire body at once
                data = json.loads(raw_bytes)
                return data

            except (
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
            ) as exc:
                last_exc = exc
                wait = 2 ** attempt
                print(
                    f"[DevSecOps Agent] Provider transfer error (attempt {attempt + 1}/3), "
                    f"retrying in {wait}s: {exc}"
                )
                time.sleep(wait)
                continue

            except requests.exceptions.HTTPError as exc:
                # If 4xx, don't retry
                if resp.status_code < 500:
                    # Try to extract error body
                    try:
                        err_body = resp.text
                    except Exception:
                        err_body = str(exc)
                    raise RuntimeError(
                        f"Provider API error {resp.status_code}: {err_body}"
                    ) from exc
                last_exc = exc
                wait = 2 ** attempt
                print(
                    f"[DevSecOps Agent] Provider server error {resp.status_code} "
                    f"(attempt {attempt + 1}/3), retrying in {wait}s"
                )
                time.sleep(wait)
                continue

            except json.JSONDecodeError as exc:
                # Got a response but it's not valid JSON — try to salvage
                raw_text = resp.text if resp else "(no response)"
                print(f"[DevSecOps Agent] Provider returned invalid JSON: {raw_text[:500]}")
                # Attempt to find JSON in the response (sometimes extra chars)
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
                raise RuntimeError(
                    f"Provider returned unparseable response: {raw_text[:200]}"
                ) from exc

        raise RuntimeError(
            f"Provider API failed after 3 attempts: {last_exc}"
        )

    # ────────────────────────────────────────
    # Main pipe method
    # ────────────────────────────────────────
    def pipe(
        self,
        user_message: str = "",
        model_id: str = "",
        messages: List[dict] = None,
        body: dict = None,
        **kwargs,
    ) -> Union[str, Generator, Iterator]:
        """
        ReAct Agentic pipeline:
        1. Take the user conversation
        2. Format MCP tools into text description for system prompt
        3. Call IBM ICA for reasoning (with tools=None to prevent 400 Bad Request)
        4. Parse response text for structured JSON tool calls:
           ```json
           {
             "tool": "tool_name",
             "arguments": { ... }
           }
           ```
        5. If found → execute via MCP, append response + result to conv, loop
        6. If not found → stream / return final answer
        """
        # Re-discover tools if cache is empty
        if not self._mcp_tools:
            self._discover_tools()

        # Handle messages input from either param or body
        conv_messages = messages
        if conv_messages is None:
            if isinstance(body, dict):
                conv_messages = body.get("messages", [])
            else:
                conv_messages = []

        # Resolve user-specific API key
        user_info = kwargs.get("__user__")
        if not user_info and isinstance(body, dict):
            user_info = body.get("user")

        user_email = ""
        if isinstance(user_info, dict):
            user_email = user_info.get("email", "")

        user_api_key = None

        # 1. First check in UserValves from Open WebUI Controls
        user_valves = None
        if isinstance(user_info, dict):
            user_valves = user_info.get("valves")
        if user_valves:
            if isinstance(user_valves, dict):
                user_api_key = user_valves.get("PROVIDER_API_KEY")
            else:
                user_api_key = getattr(user_valves, "PROVIDER_API_KEY", None)

        # 2. Second check in environment variables (for pre-configured keys)
        if not user_api_key and user_email:
            # Check in USER_KEYS_JSON mapping env var
            user_keys_json = os.getenv("USER_KEYS_JSON", "")
            if user_keys_json:
                try:
                    mapping = json.loads(user_keys_json)
                    if isinstance(mapping, dict):
                        user_api_key = mapping.get(user_email)
                except Exception as exc:
                    print(f"[DevSecOps Agent] Failed to parse USER_KEYS_JSON: {exc}")

            # Check for individual user env var, e.g. PROVIDER_API_KEY_user_example_com
            if not user_api_key:
                normalized_email = re.sub(r"[^a-zA-Z0-9_]", "_", user_email).lower()
                env_var_name = f"PROVIDER_API_KEY_{normalized_email}"
                user_api_key = os.getenv(env_var_name.upper()) or os.getenv(env_var_name)

        # Truncate printed key for security logs
        if user_api_key:
            masked_key = f"{user_api_key[:8]}...{user_api_key[-8:]}" if len(user_api_key) > 16 else "***"
            print(f"[DevSecOps Agent] Authenticated user: {user_email} (key: {masked_key})")
        else:
            print(f"[DevSecOps Agent] Authenticated user: {user_email} (using global fallback key)")

        # Build dynamic system prompt incorporating devsecops orchestrator & sub-agent instructions
        system_msg = {
            "role": "system",
            "content": self._build_system_prompt(),
        }

        # Build conversation: system + user messages
        conv = [system_msg]
        for msg in conv_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Skip empty contents or system messages if they were already injected
            if role == "system":
                continue
            conv.append({"role": role, "content": content})

        # ── Agent loop ──
        for iteration in range(self.valves.MAX_AGENT_ITERATIONS):
            print(f"[DevSecOps Agent] Iteration {iteration + 1}/{self.valves.MAX_AGENT_ITERATIONS}")
            print(f"[DevSecOps Agent] Message history length: {len(conv)} messages")

            try:
                # Always call _provider_chat with tools=None since the gateway rejects tools parameter
                data = self._provider_chat(conv, tools=None, stream=False, api_key=user_api_key)
            except RuntimeError as exc:
                print(f"[DevSecOps Agent] LLM API Error: {exc}")
                yield f"\n\n❌ **LLM Error:** {exc}"
                return
            except Exception as exc:
                print(f"[DevSecOps Agent] Unexpected LLM API Error: {exc}")
                yield f"\n\n❌ **LLM Error (unexpected):** {exc}"
                print(f"[DevSecOps Agent] Unexpected error: {traceback.format_exc()}")
                return

            # Validate response structure
            choices = data.get("choices", [])
            if not choices:
                error_msg = data.get("error", {}).get("message", str(data))
                print(f"[DevSecOps Agent] LLM returned no choices. Error: {error_msg}")
                yield f"\n\n❌ **LLM Error:** No choices in response. {error_msg}"
                return

            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            print(f"[DevSecOps Agent] LLM response (first 300 chars): {repr(content[:300])}")

            # Check if model outputs a tool call JSON structure in the text
            tool_call = None

            # 1. Try to find a JSON block in markdown
            json_block_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_block_match:
                print(f"[DevSecOps Agent] Found potential markdown JSON block")
                try:
                    parsed = json.loads(json_block_match.group(1))
                    if isinstance(parsed, dict) and "tool" in parsed:
                        tool_call = parsed
                        print(f"[DevSecOps Agent] Successfully parsed markdown JSON block as tool call: {tool_call.get('tool')}")
                except json.JSONDecodeError as exc:
                    print(f"[DevSecOps Agent] Failed to parse markdown JSON block: {exc}")
                    pass

            # 2. Try to find any curly braces block containing "tool" and "arguments"
            if not tool_call:
                braces_match = re.search(r"(\{.*?\"tool\".*?\})", content, re.DOTALL)
                if braces_match:
                    print(f"[DevSecOps Agent] Found potential raw JSON block")
                    try:
                        parsed = json.loads(braces_match.group(1))
                        if isinstance(parsed, dict) and "tool" in parsed:
                            tool_call = parsed
                            print(f"[DevSecOps Agent] Successfully parsed raw JSON block as tool call: {tool_call.get('tool')}")
                    except json.JSONDecodeError as exc:
                        print(f"[DevSecOps Agent] Failed to parse raw JSON block: {exc}")
                        pass

            if tool_call:
                # The model is requesting a tool call
                tool_name = tool_call.get("tool", "unknown")
                tool_args = tool_call.get("arguments", {})

                print(f"[DevSecOps Agent] Executing tool '{tool_name}' with args: {tool_args}")
                # Show the user what tool is being called
                yield f"\n\n🔧 **Calling tool:** `{tool_name}`\n"
                if tool_args:
                    yield f"```json\n{json.dumps(tool_args, indent=2, ensure_ascii=False)}\n```\n"

                # Execute via MCP
                try:
                    tool_result = self._call_mcp_tool(tool_name, tool_args)
                except Exception as exc:
                    tool_result = f"[Error] Tool execution failed: {exc}"
                    print(f"[DevSecOps Agent] Tool execution error: {exc}")

                print(f"[DevSecOps Agent] Tool result size: {len(tool_result)} chars")
                # Append assistant's message requesting tool call, and tool result back as user role
                conv.append({"role": "assistant", "content": content})
                conv.append({
                    "role": "user",
                    "content": f"Tool '{tool_name}' returned result:\n{tool_result[:8000]}"
                })

                yield f"\n✅ **Tool result received** ({len(tool_result)} chars)\n"

                # Continue the loop
                continue

            # ── No tool calls → final answer ──
            print(f"[DevSecOps Agent] No tool call detected in response. Returning final answer.")
            if content:
                yield f"\n\n{content}"
            else:
                yield "\n\n(No response from model)"
            return

        # Max iterations reached
        print(f"[DevSecOps Agent] Maximum iterations ({self.valves.MAX_AGENT_ITERATIONS}) reached.")
        yield "\n\n⚠️ **Agent reached maximum iterations.** Please refine your request."

    # ────────────────────────────────────────
    # Manifold: expose available models
    # ────────────────────────────────────────
    def pipelines(self) -> List[dict]:
        """Return a list of model IDs this pipeline exposes."""
        return [{"id": "devsecops-agent", "name": "DevSecOps agent"}]
