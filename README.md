# AmarktAI Marketing — LEGACY IMPLEMENTATION (DO NOT DEPLOY)

This repository is an obsolete predecessor and is **not** an authoritative production Marketing engine.

## Canonical source of truth

Use:

`sharetheherbman-debug/Amarktai-MarketingV21`

That repository is the single reusable Marketing engine for:

1. EquiProfile connected/embedded Marketing
2. AmarktAI standalone Marketing
3. future reusable white-label deployments

AmarktAI's current product purpose is preserved as the **AmarktAI standalone deployment profile** of the V21 engine. Do not revive this older implementation as a parallel runtime.

## Why this repository is retired

Historical branches in this repository contain earlier architecture, provider routing and deployment approaches that no longer match the production contract. In particular, they may reference direct providers or legacy fallbacks that conflict with the current GenX-only gateway and one-source-of-truth architecture.

The files remain in Git history for reference only. They must not be used to build, deploy, migrate, or restore current Marketing production.

## Current production rules

- canonical engine: `Amarktai-MarketingV21`
- AI gateway: GenX only
- AmarktAI domain: `https://marketing.amarktai.co.za`
- Network domain: `https://amarktai.co.za`
- no `amarktai.com`
- no copied Marketing database, Redis, scheduler or worker stack from this repository

See `docs/DEPLOYMENT_PROFILES.md` in `Amarktai-MarketingV21` for the current deployment-purpose definitions.
