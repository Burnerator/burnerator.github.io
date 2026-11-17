---
title: Same model, two worlds: NVIDIA's cloud vs. a laptop
date: 2026-11-17
summary: We ran the same open models on NVIDIA's hosted API and locally with Ollama on a MacBook. Speed, latency, accuracy, and why one cloud model timed out in our run.
tags: benchmark, nvidia, ollama, local-ai
mascot_says: I timed every hammer strike. The laptop won one round, the cloud won another, and one model never showed up to the forge.
---

**Short version:** for a 20B model, a recent laptop got all 9 scored answers right (the questions with a single correct answer), showing its first words in 1.4 s and generating ~63 tokens per second. The free NVIDIA endpoint for that same model did not answer within 3 minutes in our run. For other models, NVIDIA's cloud was fast: up to **139 tokens per second**, and answers in **under half a second**.

## What we wanted to know

Can you run "the same model" on your own laptop instead of calling a cloud API, and what do you give up? We compared NVIDIA's hosted API (`integrate.api.nvidia.com`) with [Ollama](https://ollama.com) running locally.

## The setup

- **Laptop:** Apple M5 Pro, 24 GB unified memory, Ollama 0.35.
- **Cloud:** NVIDIA API catalog, free tier.
- **Prompts:** 6 prompts, each run 3 times: `What is 17*23?`, *the capital of Australia*, *minutes between 14:35 and 17:10*, *write `is_prime(n)`*, *a one-sentence summary* and *a ~300-word explanation of hash maps*. Only the first three have a single right answer and are scored. The exact texts are in the data file below.
- **Fairness:** both sides use the same OpenAI-compatible streaming protocol. The two providers alternate who goes first, there is a warm-up call that is not measured, and every retry is recorded.
- **Which models:** only models that exist on both sides *and* fit in 24 GB. That left `gpt-oss-20b` and two Nemotron 3.5 models. Gemma 3 is listed in NVIDIA's catalog, but our account got `404 Function not found`.

## Results

| Model | Where | OK | First visible token | Speed (tok/s) | Correct answers |
|---|---|---|---|---|---|
| gpt-oss-20b | Laptop (Ollama) | 18/18 | 1.43 s | 62.8 | 100% |
| gpt-oss-20b | NVIDIA cloud | 0/18 | timed out (180 s) | — | — |
| nemotron-3.5-bolt-e4b | NVIDIA cloud | 18/18 | 0.19 s | 72.5 | 100% |
| nemotron-3.5-lightning-30b | NVIDIA cloud | 18/18 | 2.22 s | 139.1 | 78% |

*Medians over successful requests. "First visible token" is when the first words of the answer appear (reasoning models think before that); full answers took ~2.4 s for gpt-oss-20b on the laptop. "Speed" is generation speed on the long prompt. "Correct answers" counts exact answers to the 3 scored questions (9 attempts), failures count as wrong.*

## What it means (in plain words)

- **Local can beat the cloud.** In our run, NVIDIA's free `gpt-oss-20b` endpoint timed out every time, warm-up included; an earlier single test took 63 s to answer. We don't know why (heavy load is a plausible guess, not something we measured). The same model on the laptop got every scored answer right, with the first words after ~1.4 s.
- **The cloud is fast when it is available.** Nemotron Bolt replied in under half a second. Lightning generated text about **2× faster** than the laptop managed with `gpt-oss-20b`.
- **The 78% is not "dumb", it is "chatty".** Lightning *thinks out loud* before answering, and 9 of its 18 answers hit our 512-token limit before reaching the answer. A higher limit should fix most of that. We will re-run it.

## Honest limits

- This compares **deployments, not identical models**. The cloud and the laptop use different quantizations and different serving stacks.
- All times are measured **from our side**, so network latency is included.
- We have **no local Nemotron numbers yet**: our Ollama version was too old for those models. That is the next run.
- The free tier changes from hour to hour. Treat this as a snapshot, not a verdict.

## Data and code

- **Raw numbers** (sanitized), exact prompts and settings: [results.json](results.json)
- **Harness** at the exact commit used: [bench.py @ 6cd8286](https://github.com/Burnerator/anvil/blob/6cd8286a0dcb85fec7e604683e7da74d49f800c6/src/nvidia_ai/bench.py)

## Try it yourself

The harness is open source in [Burnerator/anvil](https://github.com/Burnerator/anvil):

    python -m nvidia_ai bench --pairs gpt-oss-20b --runs 3

Next on the anvil: the same benchmark with local Nemotron, and a longer token limit for the chatty models.
