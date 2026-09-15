#!/usr/bin/env python3
"""
KiloCode Model Selector Tool — Hermes tool registration
Allows agents to list, switch, and manage KiloCode gateway models
"""
import json
import subprocess
from pathlib import Path
from tools.registry import registry

CONFIG_FILE = Path("/home/agents/workspace/config/kilocode-gateway.json")

def load_config():
    if not CONFIG_FILE.exists():
        return None
    return json.loads(CONFIG_FILE.read_text())

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

def is_text_llm(model):
    """Filter to only text-to-text LLMs"""
    model_id = model['id'].lower()
    name = model.get('name', '').lower()
    
    exclude_terms = [
        'lyria', 'audio', 'music', 'tts', 'speech',
        'image', 'vision', 'visual', 'diffusion', 'dall-e', 'midjourney', 'stable-diffusion',
        'content-safety', 'safety', 'guardrail', 'moderation',
        'router', 'auto/free', 'openrouter',
        'embedding', 'embed', 'rerank',
        'whisper', 'transcribe',
        'clip',
    ]
    
    for term in exclude_terms:
        if term in model_id or term in name:
            return False
    
    arch = model.get('architecture') or {}
    modality = arch.get('modality', '')
    input_modalities = arch.get('input_modalities', [])
    output_modalities = arch.get('output_modalities', [])
    
    # If architecture info exists, validate it's text->text
    if modality and modality != 'text->text':
        return False
    if input_modalities and 'text' not in input_modalities:
        return False
    if output_modalities and 'text' not in output_modalities:
        return False
    
    return True

def kilocode_model_list(free_only: bool = True, task_id: str = None) -> str:
    """List available KiloCode gateway models (free text LLMs by default)."""
    config = load_config()
    if not config:
        return json.dumps({"error": "Config not found. Run sync first."})
    
    models = config.get('free_models' if free_only else 'paid_models', [])
    models = [m for m in models if is_text_llm(m)]
    
    if not models:
        return json.dumps({"error": "No models found", "count": 0})
    
    current = config.get('model_aliases', {}).get('current', 'unknown')
    
    result = []
    for m in models:
        result.append({
            "id": m['id'],
            "name": m.get('name', m['id']),
            "context_length": m.get('context_length'),
            "max_completion_tokens": m.get('max_completion_tokens'),
            "is_current": m['id'] == current
        })
    
    return json.dumps({
        "models": result,
        "count": len(result),
        "current": current,
        "type": "free" if free_only else "paid"
    })

def kilocode_model_current(task_id: str = None) -> str:
    """Get the currently active KiloCode model."""
    config = load_config()
    if not config:
        return json.dumps({"error": "Config not found"})
    
    current = config.get('model_aliases', {}).get('current', 'unknown')
    primary = config.get('primary_model', 'none')
    fallback = config.get('fallback_model', 'none')
    funded = config.get('deepseek_funded', False)
    
    return json.dumps({
        "current": current,
        "primary": primary,
        "primary_funded": funded,
        "fallback": fallback,
        "auto_free_router": config.get('auto_free_router', 'kilo-auto/free'),
        "last_sync": config.get('updated_at_ct', 'unknown')
    })

def kilocode_model_use(model_id: str, task_id: str = None) -> str:
    """Switch the active KiloCode model."""
    config = load_config()
    if not config:
        return json.dumps({"error": "Config not found"})
    
    aliases = config.get('model_aliases', {})
    target = aliases.get(model_id, model_id)
    
    free_ids = {m['id'] for m in config.get('free_models', []) if is_text_llm(m)}
    primary = config.get('primary_model')
    funded = config.get('deepseek_funded', False)
    
    if target not in free_ids and not (funded and target == primary):
        return json.dumps({
            "error": f"Model '{target}' not available",
            "available_free": list(free_ids),
            "primary_if_funded": primary if funded else None
        })
    
    aliases['current'] = target
    config['model_aliases'] = aliases
    save_config(config)
    
    return json.dumps({
        "success": True,
        "model": target,
        "message": f"Active model set to {target}"
    })

def kilocode_model_status(task_id: str = None) -> str:
    """Get full KiloCode gateway status."""
    config = load_config()
    if not config:
        return json.dumps({"error": "Config not found"})
    
    current = config.get('model_aliases', {}).get('current', 'unknown')
    free_models = [m for m in config.get('free_models', []) if is_text_llm(m)]
    
    return json.dumps({
        "config_file": str(CONFIG_FILE),
        "last_sync_ct": config.get('updated_at_ct', 'unknown'),
        "deepseek_funded": config.get('deepseek_funded', False),
        "current_model": current,
        "primary_model": config.get('primary_model'),
        "fallback_model": config.get('fallback_model'),
        "auto_free_router": config.get('auto_free_router'),
        "free_count": len(free_models),
        "paid_count": len([m for m in config.get('paid_models', []) if is_text_llm(m)]),
        "free_models": [{"id": m['id'], "name": m.get('name', m['id']), "current": m['id'] == current} for m in free_models],
        "aliases": config.get('model_aliases', {})
    })

def kilocode_model_sync(task_id: str = None) -> str:
    """Trigger a model list sync from KiloCode API."""
    result = subprocess.run([
        'python3', '/home/agents/workspace/scripts/kilocode-model-sync.py'
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0:
        return json.dumps({"error": f"Sync failed: {result.stderr}"})
    
    return kilocode_model_status()

# Register all tools
registry.register(
    name="kilocode_model_list",
    toolset="kilocode",
    schema={
        "name": "kilocode_model_list",
        "description": "List available KiloCode gateway models (free text LLMs by default)",
        "parameters": {
            "type": "object",
            "properties": {
                "free_only": {"type": "boolean", "default": True, "description": "List only free models"}
            },
            "required": []
        }
    },
    handler=lambda args, **kw: kilocode_model_list(args.get('free_only', True), kw.get('task_id')),
    check_fn=lambda: CONFIG_FILE.exists(),
    requires_env=[],
)

registry.register(
    name="kilocode_model_current",
    toolset="kilocode",
    schema={
        "name": "kilocode_model_current",
        "description": "Get the currently active KiloCode model",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: kilocode_model_current(kw.get('task_id')),
    check_fn=lambda: CONFIG_FILE.exists(),
    requires_env=[],
)

registry.register(
    name="kilocode_model_use",
    toolset="kilocode",
    schema={
        "name": "kilocode_model_use",
        "description": "Switch the active KiloCode model",
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {"type": "string", "description": "Model ID or alias (e.g., nemotron-ultra-free, deepseek-pro)"}
            },
            "required": ["model_id"]
        }
    },
    handler=lambda args, **kw: kilocode_model_use(args['model_id'], kw.get('task_id')),
    check_fn=lambda: CONFIG_FILE.exists(),
    requires_env=[],
)

registry.register(
    name="kilocode_model_status",
    toolset="kilocode",
    schema={
        "name": "kilocode_model_status",
        "description": "Get full KiloCode gateway status and available models",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: kilocode_model_status(kw.get('task_id')),
    check_fn=lambda: CONFIG_FILE.exists(),
    requires_env=[],
)

registry.register(
    name="kilocode_model_sync",
    toolset="kilocode",
    schema={
        "name": "kilocode_model_sync",
        "description": "Trigger a fresh model list sync from KiloCode API",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: kilocode_model_sync(kw.get('task_id')),
    check_fn=lambda: CONFIG_FILE.exists(),
    requires_env=[],
)