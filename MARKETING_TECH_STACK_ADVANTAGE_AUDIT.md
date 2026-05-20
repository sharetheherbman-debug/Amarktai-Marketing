# Marketing Tech Stack Advantage Audit

## Integrate now
- **FFmpeg**: integrate now for deterministic media processing checks.
- **LiteLLM**: integrate now for provider abstraction and routing consistency.
- **Instructor**: integrate now for structured output reliability in generation/diagnostics.

## Defer (recommended)
- **LangGraph**: defer until workflow complexity requires graph orchestration.
- **Temporal**: defer until durable long-running workflows are required at scale.
- **DSPy**: defer until enough eval data exists for prompt optimization loops.
- **Remotion**: defer until template video rendering is a product requirement.
- **Whisper.cpp**: defer unless local/offline ASR fallback is needed in production.
- **Coqui TTS**: defer unless local/offline TTS fallback becomes mandatory.
- **Qdrant**: defer until similarity memory becomes a core feature path.
- **Mem0**: defer until long-term memory product requirements are finalized.

## Risks
- Added infra/services increase ops burden and failure modes.
- Workflow engines can complicate debugging before process maturity.
- Local ML runtimes increase deployment surface and binary management overhead.

## Next steps
1. Keep current stack lean; instrument existing queue/workers first.
2. Add feature flags for any new heavy integration.
3. Re-evaluate deferred tools after production telemetry is collected.
