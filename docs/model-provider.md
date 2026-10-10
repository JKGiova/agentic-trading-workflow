# Model provider: NVIDIA NIM and DeepSeek V4.1 Flash

[Wiki home](README.md) · [Agent runtime](agent-runtime.md) · [Operating costs](deployment-and-costs.md)

**Owner selection, 2026-10-10.** Use NVIDIA's hosted NIM API with
`deepseek-ai/deepseek-v4.1-flash` for the initial analysts, Financial lead,
Bull/Bear debate, Orchestrator, Portfolio Manager and research chatbot. This
supersedes the OpenRouter/Gemini baseline proposal. LangGraph remains the framework;
NIM is the inference service, not the scheduler or memory store.

## Connection contract

| Setting | Selected target |
| --- | --- |
| Provider | NVIDIA hosted NIM API |
| Base URL | `https://integrate.api.nvidia.com/v1` |
| Chat operation | `POST /chat/completions` |
| Model ID | `deepseek-ai/deepseek-v4.1-flash` |
| Authentication | Private `TRADEBOT_NVIDIA_API_KEY`; bearer authentication through the adapter |
| Transport | Existing async HTTPX stack behind a provider-specific client |
| Initial scope | All roles use the same model, with distinct prompts, schemas and tool permissions |

The model ID and base URL are published in [NVIDIA's model-page example](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash).
NVIDIA currently lists a free prototype endpoint. Account quota, sustained throughput,
availability and any production pricing are unverified; free prototype access is
not a capacity guarantee for continuous research. This selection does not deploy
the large model locally or require an NVIDIA GPU on the CLI machine.

The owner initially requested V4 Flash, then explicitly selected V4.1 Flash after
the older free endpoint's deprecation was identified. Do not silently use the old
V4 ID, a dated variant, a partner route or a different provider.

## Runtime adapter: implemented in v0.2

`NvidiaNIM` is the default model client for research and chat. The policy explicitly
selects provider and model; OpenRouter remains an explicit compatibility choice.
The NVIDIA adapter sends the selected ID to the NVIDIA chat endpoint without
OpenRouter routing fields. It checks returned model identity and completion status,
rejecting truncated, empty, reasoning-only or unexpected native-tool responses.

Structured answers use a schema in the prompt, local Pydantic validation and one
bounded repair. Analyst research uses typed action envelopes executed by code,
so it does not depend on native function-call or server JSON-Schema enforcement.
No claim of those hosted capabilities is inferred from OpenAI compatibility.

Token-only usage retains conservative operating-cost reservations; it is not
reported as a confirmed zero-dollar bill. Concurrent monthly/cycle budgets are
enforced in storage. See [continuous runtime](continuous-runtime.md) for private
credentials, terminal/headless launch, pairing and recovery. HTTP fixtures cover
the adapter and the end-to-end team/delivery path. Actual NVIDIA latency, quota,
output quality and Telegram access remain unverified until credentials are supplied.

## Continuous-loop implications

The durable controller invokes NIM only for queued news, research questions,
cross-review, report closure or decision tasks. It does not keep model requests
open throughout X hours. Persist task/checkpoint state and evidence in PostgreSQL;
resume from recorded results after failure. Source collection and required risk
monitoring remain independent of model availability.

Start with one model for reproducible evaluations. Any later role-specific model
or reasoning change is a versioned experiment on the same frozen cases. Initial
and revised confidence remain uncalibrated estimates until prospective evaluation.

## Acceptance before enabling provider mode

- HTTP fixtures prove the NVIDIA URL, model, private bearer header and absence of
  OpenRouter routing fields, for both research and chat.
- Tests cover missing credentials, quota/transport failures, malformed/truncated
  output, absent token/billing fields, schema repair and retained spend limits.
- Tool-loop tests prove argument validation, actual result IDs, bounded rounds
  and rejection of fabricated retrieval claims.
- A real opt-in probe is reported separately from offline fixture tests; no broker
  order submission is involved.

## Primary references

- [NVIDIA DeepSeek V4.1 Flash model and example](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash)
- [NVIDIA model API reference](https://docs.api.nvidia.com/nim/reference/nvidia-deepseek-v4_1-flash)
- [Older V4 Flash availability](https://build.nvidia.com/deepseek-ai/deepseek-v4-flash)
