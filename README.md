# Open WebUI + MCP Agent Pipeline

A self-contained deployment of **Open WebUI** with a custom **Pipeline Agent** that connects to your MCP Gateway and uses **IBM ICA** as the LLM backend.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Open WebUI  │────▶│  Pipelines       │────▶│  MCP Gateway        │
│  :3000       │     │  :9099           │     │  (GitLab, Jenkins,  │
│              │     │                  │────▶│   Harbor, K8s, …)   │
│              │     │  mcp_agent_      │     └─────────────────────┘
│              │     │  pipeline.py     │
│              │     │                  │────▶┌─────────────────────┐
└─────────────┘     └──────────────────┘     │  IBM ICA API        │
                                              │  sg.ica.ibm.com     │
                                              └─────────────────────┘
```

## Quick Start

### 1. Clone & configure

```bash
git clone <this-repo>
cd ai-content
```

Edit the `.env` file and verify all values are correct:

```bash
cat .env
```

### 2. Start the stack

```bash
docker compose up -d
```

### 3. Access Open WebUI

Open [http://localhost:3000](http://localhost:3000) in your browser.

1. Create an admin account on first login
2. In the model selector, choose **"MCP Agent"** — this is your pipeline
3. Start chatting! Ask things like:
   - *"List all GitLab projects"*
   - *"Show me the latest Jenkins build for project X"*
   - *"What are the recent findings in DefectDojo?"*

## Configuration

All settings are configurable in two ways:

### Environment Variables (`.env`)

| Variable | Description |
|----------|-------------|
| `ICA_API_BASE` | IBM ICA API base URL |
| `ICA_API_KEY` | IBM ICA Bearer token |
| `MCP_GATEWAY_URL` | MCP Gateway HTTP endpoint |
| `MCP_LITELLM_API_KEY` | LiteLLM API key header |
| `MCP_DD_API_KEY` | DataDog API key header |
| `MCP_HARBOR_URL` | Harbor registry URL |
| `MCP_HARBOR_USERNAME` | Harbor username |
| `MCP_HARBOR_PASSWORD` | Harbor password |
| `MCP_GITLAB_TOKEN` | GitLab Personal Access Token |
| `MCP_JENKINS_URL` | Jenkins URL |
| `MCP_JENKINS_USERNAME` | Jenkins username |
| `MCP_JENKINS_PASSWORD` | Jenkins password |

### Pipeline Valves (UI)

In Open WebUI, go to **Admin Panel → Settings → Pipelines** and click on the **MCP Agent** pipeline to edit its Valves:

- **ICA_MODEL_ID** — Change the model (default: `granite-3.1-8b-instruct`)
- **ICA_MAX_TOKENS** — Max response length (default: `4096`)
- **ICA_TEMPERATURE** — Sampling temperature (default: `0.2`)
- **MAX_AGENT_ITERATIONS** — Max tool-call loops (default: `10`)

## How It Works

The pipeline implements an **agent loop**:

```
User Message
    │
    ▼
┌────────────────────────┐
│  1. Discover MCP tools │ ◄── tools/list via MCP Gateway
│  2. Convert to OpenAI  │
│     function format    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  3. Send messages +    │
│     tool definitions   │ ──▶ IBM ICA (chat/completions)
│     to LLM             │
└────────┬───────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 tool_calls   text response
    │              │
    ▼              ▼
┌──────────┐  ┌──────────┐
│ Execute  │  │ Return   │
│ via MCP  │  │ to user  │
│ Gateway  │  │          │
└────┬─────┘  └──────────┘
     │
     └──▶ Append result to conversation, loop back to step 3
```

## Troubleshooting

### Check pipeline logs

```bash
docker compose logs -f pipelines
```

### Check Open WebUI logs

```bash
docker compose logs -f open-webui
```

### Pipeline not showing up?

Make sure the `./pipelines` directory is mounted correctly:

```bash
docker compose exec pipelines ls /app/pipelines/
```

### MCP tools not discovered?

Check if the MCP gateway is reachable from the container:

```bash
docker compose exec pipelines curl -s http://ai-gateway.vayu.devopsnonprd.vayuktbcs/mcp
```

## File Structure

```
ai-content/
├── .env                              # Secrets & configuration
├── docker-compose.yml                # Docker stack definition
├── pipelines/
│   └── mcp_agent_pipeline.py         # MCP Agent Pipeline
└── README.md                         # This file
```
