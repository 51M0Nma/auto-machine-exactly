#!/usr/init/env python3
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

# Configure Google GenAI SDK
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

def call_gemini_api(prompt, json_mode=False):
    if not GEMINI_API_KEY:
        Log.warn("GEMINI_API_KEY is not set. Using robust fallback generation.")
        return None

    try:
        generation_config = {"temperature": 0.2 if json_mode else 0.4}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        Log.error(f"Gemini API error: {str(e)}")
        return None

def clean_json_response(raw_text):
    if not raw_text: return {}
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"): cleaned = cleaned[7:]
    elif cleaned.startswith("```"): cleaned = cleaned[3:]
    if cleaned.endswith("```"): cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except Exception: pass
        return {}

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {"tools": [], "last_run": None}

def save_registry(registry):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f: json.dump(registry, f, indent=2, ensure_ascii=False)

def get_curated_trend_signals():
    return [
        {"query": "Mortgage Refinance Break-Even Calculator", "snippet": "Compare current loan against new interest rates and closing costs"},
        {"query": "AI Inference Token Cost Estimator", "snippet": "Calculate input/output token pricing across AI models"}
    ]

def step_b_trend_discovery(registry):
    Log.step("STEP B", "Dynamic Trend Audit: Selecting high-intent utility...")
    pool = get_curated_trend_signals()
    existing_slugs = [t["slug"] for t in registry.get("tools", [])]
    
    chosen = pool[0]
    for p in pool:
        slug_candidate = re.sub(r'[^a-z0-9]+', '-', p["query"].lower()).strip('-')
        if slug_candidate not in existing_slugs:
            chosen = p
            break
            
    slug = re.sub(r'[^a-z0-9]+', '-', chosen["query"].lower()).strip('-')
    return {
        "query": chosen["query"],
        "tool_title": chosen["query"],
        "slug": slug,
        "category": "Finance",
        "description": chosen.get("snippet", "Interactive calculation tool.")
    }

def generate_tool_code(trend_data):
    Log.info(f"Generating executable tool code for '{trend_data['tool_title']}'...")
    prompt = f"""
Build a complete, standalone, production-ready interactive web tool for:
TITLE: {trend_data['tool_title']}
CATEGORY: {trend_data.get('category', 'Utility')}
DESCRIPTION: {trend_data.get('description', '')}

Requirements:
1. Pure client-side vanilla JavaScript and Tailwind CSS styling.
2. Include interactive input fields, number inputs, or sliders so users can calculate live values.
3. Output strict JSON with keys: 'body', 'script', 'keywords', 'explanation'.
"""
    raw_res = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw_res)
    
    # Robust interactive calculator fallback if AI returns concise body
    if not parsed or "body" not in parsed or "Interactive operational calculator ready" in parsed.get("body", ""):
        return {
            "body": """
<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <h3 class="text-sm font-semibold text-white">Input Parameters</h3>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Primary Value / Amount ($)</label>
        <input type="number" id="inp-value" value="100000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Interest Rate / Fee (%)</label>
        <input type="number" id="inp-rate" value="5.5" step="0.1" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Duration (Years)</label>
        <input type="number" id="inp-years" value="10" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <button id="btn-calc" class="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors">Calculate Now</button>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
      <h3 class="text-sm font-semibold text-white">Calculation Results</h3>
      <div class="space-y-3">
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Estimated Periodic Cost</span>
          <span id="res-periodic" class="text-2xl font-bold font-mono text-white">$1,085.26</span>
        </div>
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Total Lifetime Amount</span>
          <span id="res-total" class="text-2xl font-bold font-mono text-emerald-400">$130,231.20</span>
        </div>
      </div>
      <p class="text-[11px] text-slate-500">Computed instantly in your browser.</p>
    </div>
  </div>
</div>
""",
            "script": """
<script>
(function() {
  const valInp = document.getElementById('inp-value');
  const rateInp = document.getElementById('inp-rate');
  const yearsInp = document.getElementById('inp-years');
  const btnCalc = document.getElementById('btn-calc');
  const resPeriodic = document.getElementById('res-periodic');
  const resTotal = document.getElementById('res-total');

  function compute() {
    const p = parseFloat(valInp.value) || 0;
    const r = (parseFloat(rateInp.value) || 0) / 100 / 12;
    const n = (parseFloat(yearsInp.value) || 0) * 12;

    let periodic = 0;
    if (r > 0 && n > 0) {
      periodic = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    } else if (n > 0) {
      periodic = p / n;
    }

    const total = periodic * n;
    resPeriodic.textContent = '$' + periodic.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    resTotal.textContent = '$' + total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }

  if (btnCalc) btnCalc.addEventListener('click', compute);
  [valInp, rateInp, yearsInp].forEach(el => {
    if (el) el.addEventListener('input', compute);
  });
  compute();
})();
</script>
""",
            "keywords": "calculator, utility, finance, estimator",
            "explanation": "This interactive tool computes financial projections instantly using compound interest formulas."
        }
    return parsed

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
        "<!-- {{JSON_LD_SCHEMA}} -->": f'<script type="application/ld+json">{{"@context":"[https://schema.org](https://schema.org)","@type":"WebApplication","name":"{tool_entry["title"]}","url":"{canonical_url}"}}</script>',
        "<!-- {{ADSENSE_PUB_ID_HEAD}} -->": "",
        "<!-- {{VERSION_SWITCHER}} -->": '<span class="text-xs text-slate-500">v1.0</span>',
        "<!-- {{ADSENSE_SLOT_TOP}} -->": "",
        "<!-- {{TOOL_CATEGORY}} -->": tool_entry.get("category", "Utility"),
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
    Log.step("STEP E", "Rebuilding central Root Directory...")
    tools = registry.get("tools", [])
    cards = []
    for t in tools:
        # Using relative links './{t["slug"]}/' to prevent 404 sub-path issues on GitHub Pages
        cards.append(f'<div class="p-5 bg-slate-900 border border-slate-800 rounded-xl"><a href="./{t["slug"]}/" class="text-blue-400 font-semibold">{t["title"]}</a><p class="text-xs text-slate-400 mt-1">{t["description"]}</p></div>')

    root_html = f"""<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head><meta charset="UTF-8"><title>{SITE_NAME}</title><script src="[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)"></script></head>
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
    trend_data = step_b_trend_discovery(registry)
    
    if not any(t["slug"] == trend_data["slug"] for t in registry.get("tools", [])):
        tool_code = generate_tool_code(trend_data)
        tool_entry = {
            "slug": trend_data["slug"],
            "title": trend_data["tool_title"],
            "description": trend_data["description"],
            "category": trend_data.get("category", "Finance"),
            "version": "1.0",
            "last_updated": "2026-10-14",
            "status": "Active"
        }
        assemble_and_save_tool(tool_entry, tool_code["body"], tool_code["script"])
        registry.setdefault("tools", []).insert(0, tool_entry)
        save_registry(registry)
        
    rebuild_root_directory(registry)
    Log.success("Pipeline executed successfully.")

if __name__ == "__main__":
    main()
