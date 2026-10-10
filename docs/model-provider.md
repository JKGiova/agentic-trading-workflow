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
| Authentication | Private `NVIDIA_API_KEY`; bearer authentication through the adapter |
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

## Runtime migration: pending

Current v0.1 still instantiates the OpenRouter client and expects
`TRADEBOT_OPENROUTER_API_KEY`. No NVIDIA call has been made and no NVIDIA credential
has been added to git. The settings above describe the next adapter migration,
not working current CLI environment variables.

1. Introduce explicit provider/model settings and a private NVIDIA credential.
   Wire the NVIDIA adapter into research and chatbot creation; update doctor,
   sample policy and CLI instructions together. Missing credentials fail clearly.
2. Use the NVIDIA request contract. Remove OpenRouter-only routing fields rather
   than changing only the hostname. Validate endpoint output, completion status,
   token usage and requested/returned model identity; never treat truncated or
   reasoning-only content as a completed assessment.
3. Check native function calling, tool-result turns and structured-output support
   against the exact hosted endpoint. OpenAI-compatible chat transport alone does
   not establish JSON Schema enforcement or tool support. If a capability is
   absent, use an explicit tested typed-action/JSON validation path, or mark the
   required capability unavailable; do not pretend a tool ran.
4. Preserve current input/output limits, concurrency caps, one bounded schema
   repair and cost reservations. NVIDIA usage may report tokens without an
   OpenRouter-style billed `usage.cost`; keep usage, configured cost estimates and
   provider-confirmed billing separate. Unknown billing must not become zero cost.
5. Run a bounded opt-in probe for JSON reports and a read-only tool round trip,
   recording latency, actual usage, limits and capability gaps. Credentials stay
   in environment/secret storage and outside prompts, logs and reports.

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
