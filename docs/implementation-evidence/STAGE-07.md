# Stage 07 — Together AI interpretation; voice completed last

13 October 2026. The owner selected Together AI, supplied a private key, then instructed text-first end-to-end completion with voice last. The key is in ignored backend/.env and is never returned to the browser.

One bounded interpreter extracts strict semantic intentions and exact evidence spans. Qwen/Qwen3.5-9B uses Together structured JSON; unsupported fields, recipients, tools, ungrounded quantities/dates and malformed output are rejected, with one repair attempt maximum. The server owns customer, product, policy and facts binding. No model-authored price, discount, checkout URL or payment claim is rendered as truth.

Explicit opt-out/support/refusal runs before the model and persists even during provider failure. Compound intentions are preserved with a deterministic validation layer. Responses use scoped facts and fixed templates; vague dates require explicit future IST confirmation. Exact same-product/quantity and independent WhatsApp handoff confirmation feed the Stage 05 quote/digest/cart pipeline. Link sending remains a separate Stage 04 approval.

Consented operator conversation sessions are Demo-only, expire after 15 minutes and allow at most 20 sequenced turns. Typed turns deduplicate by input hash/sequence. A processing claim and protective hold commit before the external API request. Stop cancels pending turns and discards late replies; external requests never run under a long database transaction. Historical sessions/transcripts are recovered on page reload.

Optional browser voice is collapsed under the text workflow. Short WebM/WAV uploads use Together Parakeet, wait for explicit transcript review, then use the same interpreter. Kokoro speech renders only the server reply. Start/finish/mute/stop controls release microphone tracks, cancel local playback and clear object URLs. Raw browser audio is not retained in the application database. This is not a telephone agent or a production customer voice session.

## Actual provider evidence

- Real structured compound-intent smoke check passed, 6,390 ms and 568 tokens.
- Real transcription of a locally synthesized, non-customer recording passed in 2,000 ms.
- Real Kokoro speech generation passed in 1,109 ms (80,256 audio bytes).
- A seven-case adjudicated synthetic set recorded raw v1 Together exact intent sets on 5/7, versus deterministic baseline 7/7, median Together latency 1,562 ms. Original results are preserved. Deterministic protective/compound validation replay yields 7/7 on these same cases; this is not a generalization claim. Prompt v2 clarifies support, purchase statements and compound enquiries; the end-to-end browser used v2.
- Prompt/schema/model, key fingerprint, facts, latency, usage and validation outcome are persisted. Catalog-based cost estimates are labelled estimates; actual billed cost is unknown. The key itself is not stored in traces.

See stage-07-together-source.json, stage-07-audio-source.json and stage-07-evaluation.json. Official references: [structured output](https://docs.together.ai/docs/inference/chat/structured-outputs), [models/pricing](https://docs.together.ai/docs/serverless/models), [transcription](https://docs.together.ai/docs/inference/transcription/overview), [speech](https://docs.together.ai/docs/inference/text-to-speech/overview).

Backend tests cover schema repair bounds, injection/recipient fields, grounded spans/quantities, explicit consent, duplicate turns, stop during a delayed model, transcript review, failed models, opt-out, ambiguous dates and checkout consent. Latest integrated evidence is in STAGE-09.md; earlier stage-07-tests.txt is retained. Provider-only final checks passed four tests. Voice was exercised only after the full text-to-outcomes browser flow.

Configured defaults: TOGETHER_CHAT_MODEL=Qwen/Qwen3.5-9B, TOGETHER_STT_MODEL=nvidia/parakeet-tdt-0.6b-v3, TOGETHER_TTS_MODEL=hexgrad/Kokoro-82M, TOGETHER_TTS_VOICE=af_heart. TOGETHER_API_KEY is server-side only. Browser model tests send synthetic customer utterances with explicit processing consent; real Shopify contacts are not forwarded.
