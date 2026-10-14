#!/usr/bin/env python3
"""
Autonomous Self-Coding Micro-Tool Network - Master Orchestrator
"""

import os
import sys
import json
import random
import re
from datetime import datetime, timezone
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_URL = os.environ.get("SITE_URL", "https://51m0nma.github.io/auto-machine-exactly").rstrip("/")
SITE_NAME = os.environ.get("SITE_NAME", "OmniTools Network")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(ROOT_DIR, "tools_registry.json")
ERROR_LOG_FILE = os.path.join(ROOT_DIR, "error_log.json")
TEMPLATE_FILE = os.path.join(ROOT_DIR, "template.html")
ROOT_INDEX_FILE = os.path.join(ROOT_DIR, "index.html")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class Log:
    @classmethod
    def info(cls, msg): print(f"[INFO] {msg}", flush=True)
    @classmethod
    def step(cls, step_name, msg): print(f"\n==> [{step_name}] {msg}", flush=True)
    @classmethod
    def success(cls, msg): print(f"[SUCCESS] {msg}", flush=True)
    @classmethod
    def warn(cls, msg): print(f"[WARN] {msg}", flush=True)
    @classmethod
    def error(cls, msg): print(f"[ERROR] {msg}", flush=True)

def generate_tool_code(trend_data):
    Log.info(f"Generating executable tool code for '{trend_data['tool_title']}'...")
    return {
        "body": """
<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <h3 class="text-sm font-semibold text-white">Input Parameters</h3>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Input / Prompt Tokens (Count)</label>
        <input type="number" id="inp-tokens" value="50000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Output / Completion Tokens (Count)</label>
        <input type="number" id="out-tokens" value="10000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Model Rate ($ per 1M tokens)</label>
        <input type="number" id="model-rate" value="0.50" step="0.05" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <button id="btn-calc" class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors">Calculate Estimated Cost</button>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
      <h3 class="text-sm font-semibold text-white">Estimated Inference Expenses</h3>
      <div class="space-y-3">
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Total Token Volume</span>
          <span id="res-volume" class="text-2xl font-bold font-mono text-white">60,000 Tokens</span>
        </div>
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Total Estimated Cost</span>
          <span id="res-cost" class="text-2xl font-bold font-mono text-emerald-400">$0.03</span>
        </div>
      </div>
      <p class="text-[11px] text-slate-500">Computed instantly in your browser based on active pricing parameters.</p>
    </div>
  </div>
</div>
""",
        "script": """
<script>
(function() {
  const inpTokens = document.getElementById('inp-tokens');
  const outTokens = document.getElementById('out-tokens');
  const modelRate = document.getElementById('model-rate');
  const btnCalc = document.getElementById('btn-calc');
  const resVolume = document.getElementById('res-volume');
  const resCost = document.getElementById('res-cost');

  function compute() {
    const inCount = parseFloat(inpTokens.value) || 0;
    const outCount = parseFloat(outTokens.value) || 0;
    const rate = parseFloat(modelRate.value) || 0;

    const totalTokens = inCount + outCount;
    const cost = (totalTokens / 1000000) * rate;

    resVolume.textContent = totalTokens.toLocaleString() + ' Tokens';
    resCost.textContent = '$' + cost.toLocaleString(undefined, {minimumFractionDigits: 4, maximumFractionDigits: 4});
  }

  if (btnCalc) btnCalc.addEventListener('click', compute);
  [inpTokens, outTokens, modelRate].forEach(el => {
    if (el) el.addEventListener('input', compute);
  });
  compute();
})();
</script>
""",
        "keywords": "calculator, utility, ai tokens, cost estimator",
        "explanation": "This interactive tool calculates estimated inference expenditure based on combined prompt and completion token volumes."
    }

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {"tools": [], "last_run": None}

def save_registry(registry):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f: json.dump(registry, f, indent=2, ensure_ascii=False)

def assemble_and_save_tool(tool_entry, body_html, script_html):
    if not os.path.exists(TEMPLATE_FILE): return
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f: template = f.read()

    slug = tool_entry["slug"]
    tool_dir = os.path.join(ROOT_DIR, slug)
    os.makedirs(tool_dir, exist_ok=True)
    canonical_url = f"{SITE_URL}/{slug}/"

    replacements = {
        "<!-- {{TOOL_TITLE}} -->": tool_entry["title"],
        "<!-- {{SITE_NAME}} -->": SITE_NAME,
        "<!-- {{TOOL_META_DESCRIPTION}} -->": tool_entry["description"],
        "<!-- {{TOOL_KEYWORDS}} -->": tool_entry.get("keywords", ""),
        "<!-- {{TOOL_CANONICAL_URL}} -->": canonical_url,
        "<!-- {{JSON_LD_SCHEMA}} -->": f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebApplication","name":"{tool_entry["title"]}","url":"{canonical_url}"}}</script>',
        "<!-- {{ADSENSE_PUB_ID_HEAD}} -->": "",
        "<!-- {{VERSION_SWITCHER}} -->": '<span class="text-xs text-slate-500">v1.0</span>',
        "<!-- {{ADSENSE_SLOT_TOP}} -->": "",
        "<!-- {{TOOL_CATEGORY}} -->": tool_entry.get("category", "Finance"),
        "<!-- {{TOOL_UPDATED_DATE}} -->": "2026-10-14",
        "<!-- {{TOOL_VERIFICATION_STATUS}} -->": "Active",
        "<!-- {{TOOL_HEADER_SUBTITLE}} -->": tool_entry["description"],
        "<!-- {{TOOL_BODY}} -->": body_html,
        "<!-- {{TOOL_EXPLANATION}} -->": tool_entry.get("explanation", ""),
        "<!-- {{TOOL_SCRIPT}} -->": script_html,
        "<!-- {{ADSENSE_SLOT_BOTTOM}} -->": "",
        "<!-- {{TOOL_SLUG}} -->": slug,
    }

    final_html = template
    for placeholder, val in replacements.items():
        final_html = final_html.replace(placeholder, str(val))

    with open(os.path.join(tool_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)

def rebuild_root_directory(registry):
    tools = registry.get("tools", [])
    cards = []
    for t in tools:
        cards.append(f'<div class="p-5 bg-slate-900 border border-slate-800 rounded-xl"><a href="./{t["slug"]}/" class="text-blue-400 font-semibold">{t["title"]}</a><p class="text-xs text-slate-400 mt-1">{t["description"]}</p></div>')

    root_html = f"""<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head><meta charset="UTF-8"><title>{SITE_NAME}</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="p-10 max-w-4xl mx-auto">
  <h1 class="text-3xl font-bold mb-4">{SITE_NAME}</h1>
  <p class="text-slate-400 mb-8">Autonomous Micro-Tool Network</p>
  <div class="grid gap-4">{"".join(cards)}</div>
</body>
</html>"""
    with open(ROOT_INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(root_html)

def main():
    registry = load_registry()
    tool_entry = {
        "slug": "ai-inference-token-cost-estimator",
        "title": "AI Inference Token Cost Estimator",
        "description": "Calculate input/output token pricing across AI models",
        "category": "Finance",
        "version": "1.0",
        "last_updated": "2026-10-14",
        "status": "Active"
    }
    tool_code = generate_tool_code(tool_entry)
    assemble_and_save_tool(tool_entry, tool_code["body"], tool_code["script"])
    
    if not any(t["slug"] == tool_entry["slug"] for t in registry.get("tools", [])):
        registry.setdefault("tools", []).insert(0, tool_entry)
        save_registry(registry)
        
    rebuild_root_directory(registry)
    Log.success("Pipeline executed successfully.")

if __name__ == "__main__":
    main()
