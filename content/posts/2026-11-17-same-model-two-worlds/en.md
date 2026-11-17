---
title: Same model, two worlds: NVIDIA's cloud vs. a laptop
date: 2026-11-17
summary: We ran the same open models on NVIDIA's hosted API and locally with Ollama on a MacBook. Speed, latency, accuracy, and why one cloud model never answered at all.
tags: benchmark, nvidia, ollama, local-ai
mascot_says: I timed every hammer strike. The laptop won one round, the cloud won another, and one model never showed up to the forge.
---

**Short version:** for a 20B model, a recent laptop answered every question correctly at ~63 tokens per second, while the free NVIDIA endpoint for that same model never answered within 3 minutes. For other models, NVIDIA's cloud was fast: up to **139 tokens per second**, and answers in **under half a second**.

## What we wanted to know

Can you run "the same model" on your own laptop instead of calling a cloud API, and what do you give up? We compared NVIDIA's hosted API (`integrate.api.nvidia.com`) with [Ollama](https://ollama.com) running locally.

## The setup

- **Laptop:** Apple M5 Pro, 24 GB unified memory, Ollama 0.35.
- **Cloud:** NVIDIA API catalog, free tier.
- **Prompts:** 6 prompts (arithmetic, a capital city, a time difference, writing a small function, a one-sentence summary and a ~300-word explanation), each run 3 times.
- **Fairness:** both sides use the same OpenAI-compatible streaming protocol. The two providers alternate who goes first, there is a warm-up call that is not measured, and every retry is recorded.
- **Which models:** only models that exist on both sides *and* fit in 24 GB. That left `gpt-oss-20b` and two Nemotron 3.5 models. Gemma 3 is listed in NVIDIA's catalog, but our account got `404 Function not found`.

## Results

| Model | Where | OK | First visible token | Speed (tok/s) | Correct answers |
|---|---|---|---|---|---|
| gpt-oss-20b | Laptop (Ollama) | 18/18 | 1.43 s | 62.8 | 100% |
| gpt-oss-20b | NVIDIA cloud | 0/18 | did not answer within 180 s | — | — |
| nemotron-3.5-bolt-e4b | NVIDIA cloud | 18/18 | 0.19 s | 72.5 | 100% |
| nemotron-3.5-lightning-30b | NVIDIA cloud | 18/18 | 2.22 s | 139.1 | 78% |

*Medians. "Speed" is generation speed on the long prompt. "Correct" counts exact answers to the questions with a single right answer.*

## What it means (in plain words)

- **Local can beat the cloud.** On the free tier, NVIDIA's `gpt-oss-20b` endpoint was too congested to answer at all, even after a warm-up. The same model on the laptop answered every question correctly in about a second and a half.
- **The cloud is fast when it is available.** Nemotron Bolt replied in under half a second. Lightning generated text about **2× faster** than the laptop managed with `gpt-oss-20b`.
- **The 78% is not "dumb", it is "chatty".** Lightning *thinks out loud* before answering, and 9 of its 18 answers hit our 512-token limit before reaching the answer. A higher limit should fix most of that. We will re-run it.

## Honest limits

- This compares **deployments, not identical models**. The cloud and the laptop use different quantizations and different serving stacks.
- All times are measured **from our side**, so network latency is included.
- We have **no local Nemotron numbers yet**: our Ollama version was too old for those models. That is the next run.
- The free tier changes from hour to hour. Treat this as a snapshot, not a verdict.

## Try it yourself

The harness is open source in [Burnerator/anvil](https://github.com/Burnerator/anvil):

    python -m nvidia_ai bench --pairs gpt-oss-20b --runs 3

Next on the anvil: the same benchmark with local Nemotron, and a longer token limit for the chatty models.
