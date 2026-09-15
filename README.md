# Altair — Customized Hermes Agent Fork

A customized fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by
Nous Research — the open-source agent framework.

This fork powers **Altair**, a Senior VP agent running a production multi-agent
ecosystem on self-hosted hardware: 8 agents, 16 specialized workers, a PostgreSQL-backed
knowledge architecture, and SEC EDGAR data pipelines — all on a ~$1,600 machine built from a barebones mini-PC
plus self-sourced RAM and storage.

## Customizations

Six modifications on `main`, above the `altair-baseline-2026-09-14` tag:

- `plugins/model-providers/kilocode/__init__.py` — KiloCode model provider integration
- `hermes_cli/models.py` — model catalog
- `hermes_cli/model_switch.py` — model switch logic
- `hermes_cli/inventory.py` — inventory tracking
- `cron/lifecycle_guard.py` — cron lifecycle guard
- `tools/kilocode_model_selector.py` — model selector tool

## Update policy

Selective, not automatic. The upstream remote (`NousResearch/hermes-agent`) is reviewed
and cherry-picked only when a change advances the ecosystem. Patches that don't improve
the agent's functionality are skipped.

## Upstream

Full documentation and install instructions: https://github.com/NousResearch/hermes-agent
