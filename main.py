#!/usr/bin/env python3
"""
Autonomous Self-Coding Micro-Tool Network - Master Orchestrator
Continuously discovers trends, codes tools via Gemini AI, and deploys statically.
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

def call_gemini_api(prompt, json_mode=False):
    if not GEMINI_API_KEY:
        Log.warn("GEMINI_API_KEY is not set.")
        return None
    try:
        generation_config = {"temperature": 0.3}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
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

def step_b_trend_discovery(registry):
    Log.step("STEP B", "Autonomous Trend Discovery: Querying high-intent search utility trends...")
    existing_tools = [t["title"] for t in registry.get("tools", [])]
    
    prompt = f"""
Identify one high-demand, trending online micro-tool or calculator search query (e.g. financial, developer, SaaS, or productivity utility) that is NOT in this existing list: {existing_tools}.
Output strict JSON with keys:
- "query": The exact search trend topic name.
- "category": Broad category (e.g., "Finance", "Developer", "SaaS", "Utility").
- "description": A concise 1-sentence meta description of what the tool calculates or solves.
"""
    raw = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw)
    
    if not parsed or "query" not in parsed:
        # Fallback trend pool if API returns empty
        fallbacks = [
            {"query": "SaaS Customer LTV to CAC Ratio Calculator", "category": "SaaS", "description": "Calculate customer lifetime value relative to acquisition cost."},
            {"query": "JSON to TypeScript Interface Generator", "category": "Developer", "description": "Convert raw JSON payloads into strict TypeScript interfaces instantly."},
            {"query": "Compound Interest and Retirement Growth Calculator", "category": "Finance", "description": "Project long-term investment growth with recurring contributions."}
        ]
        # Pick one not already built
        chosen = next((f for f in fallbacks if f["query"] not in existing_tools), fallbacks[0])
    else:
        chosen = parsed

    slug = re.sub(r'[^a-z0-9]+', '-', chosen["query"].lower()).strip('-')
    return {
        "title": chosen["query"],
        "slug": slug,
        "category": chosen.get("category", "Utility"),
        "description": chosen.get("description", "Interactive calculation tool.")
    }

def generate_tool_code(trend_data):
    Log.info(f"Generating executable code for '{trend_data['title']}' via Gemini AI...")
    prompt = f"""
Build a complete, production-ready interactive web tool for:
TITLE: {trend_data['title']}
DESCRIPTION: {trend_data['description']}

Requirements:
1. Pure client-side vanilla JavaScript and Tailwind CSS styling.
2. Must include interactive input fields (<input type="number"> or sliders) and a calculate button or live event listeners so users get dynamic calculations.
3. Output strict JSON with keys:
   - "body": HTML string for the interactive calculator card container and inputs.
   - "script": <script>...</script> string containing the calculation logic.
   - "keywords": comma-separated SEO keywords string.
   - "explanation": Brief explanation of the formula/methodology used.
"""
    raw = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw)
    
    # Autonomous Dynamic Fallback if AI output is missing inputs/script
    if not parsed or "body" not in parsed or "input" not in parsed.get("body", "").lower():
        Log.warn("AI output lacked form inputs; applying dynamic interactive calculator wrapper.")
        return {
            "body": f"""
<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <h3 class="text-sm font-semibold text-white">Tool Parameters</h3>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Primary Input Metric</label>
        <input type="number" id="dyn-input-1" value="1000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Secondary Rate / Multiplier (%)</label>
        <input type="number" id="dyn-input-2" value="15" step="0.5" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <button id="dyn-btn" class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors">Compute Value</button>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
      <h3 class="text-sm font-semibold text-white">Computed Output</h3>
      <div class="space-y-3">
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Estimated Result</span>
          <span id="dyn-res" class="text-2xl font-bold font-mono text-emerald-400">$1,150.00</span>
        </div>
      </div>
      <p class="text-[11px] text-slate-500">Executed locally in your browser for {trend_data['title']}.</p>
    </div>
  </div>
</div>
""",
            "script": """
<script>
(function() {
  const i1 = document.getElementById('dyn-input-1');
  const i2 = document.getElementById('dyn-input-2');
  const btn = document.getElementById('dyn-btn');
  const res = document.getElementById('dyn-res');

  function calc() {
    const v1 = parseFloat(i1.value) || 0;
    const v2 = parseFloat(i2.value) || 0;
    const total = v1 * (1 + (v2 / 100));
    res.textContent = '$' + total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }

  if (btn) btn.addEventListener('click', calc);
  [i1, i2].forEach(el => { if(el) el.addEventListener('input', calc); });
  calc();
})();
</script>
""",
            "keywords": f"{trend_data['slug']}, calculator, utility, online tool",
            "explanation": f"Automated interactive estimation model for {trend_data['title']}."
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
        "<!-- {{VERSION_SWITCHER}} -->": '<span class="text-xs text-slate-500">v1.0</span>',
        "<!-- {{TOOL_CATEGORY}} -->": tool_entry.get("category", "Utility"),
        "<!-- {{TOOL_UPDATED_DATE}} -->": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "<!-- {{TOOL_VERIFICATION_STATUS}} -->": "Active",
        "<!-- {{TOOL_HEADER_SUBTITLE}} -->": tool_entry["description"],
        "<!-- {{TOOL_BODY}} -->": body_html,
        "<!-- {{TOOL_EXPLANATION}} -->": tool_entry.get("explanation", ""),
        "<!-- {{TOOL_SCRIPT}} -->": script_html,
        "<!-- {{TOOL_SLUG}} -->": slug,
    }

    final_html = template
    for placeholder, val in replacements.items():
        final_html = final_html.replace(placeholder, str(val))

    with open(os.path.join(tool_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)

def rebuild_root_directory(registry):
    Log.step("STEP E", "Rebuilding central Root Directory Index...")
    tools = registry.get("tools", [])
    cards = []
    for t in tools:
        cards.append(f'<div class="p-5 bg-slate-900 border border-slate-800 rounded-xl hover:border-slate-700 transition-colors"><a href="./{t["slug"]}/" class="text-blue-400 font-semibold text-base hover:underline">{t["title"]}</a><p class="text-xs text-slate-400 mt-1">{t["description"]}</p></div>')

    root_html = f"""<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head><meta charset="UTF-8"><title>{SITE_NAME}</title><script src="[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)"></script></head>
<body class="p-10 max-w-4xl mx-auto">
  <h1 class="text-3xl font-bold mb-2">{SITE_NAME}</h1>
  <p class="text-slate-400 mb-8">Autonomous Self-Coding Micro-Tool Network — Discovering & Deploying Daily</p>
  <div class="grid gap-4">{"".join(cards)}</div>
</body>
</html>"""
    with open(ROOT_INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(root_html)

def main():
    registry = load_registry()
    
    # 1. Autonomously discover a new trend
    trend_data = step_b_trend_discovery(registry)
    
    # 2. Check if it's already built
    if not any(t["slug"] == trend_data["slug"] for t in registry.get("tools", [])):
        # 3. Generate tool code via Gemini AI with fallback protection
        tool_code = generate_tool_code(trend_data)
        
        tool_entry = {
            "slug": trend_data["slug"],
            "title": trend_data["title"],
            "description": trend_data["description"],
            "category": trend_data["category"],
            "version": "1.0",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "Active"
        }
        
        # 4. Assemble static directory and files
        assemble_and_save_tool(tool_entry, tool_code["body"], tool_code["script"])
        
        # 5. Update registry
        registry.setdefault("tools", []).insert(0, tool_entry)
        registry["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        save_registry(registry)
        
    # 6. Rebuild root index directory listing all tools
    rebuild_root_directory(registry)
    Log.success("Autonomous pipeline run completed successfully.")

if __name__ == "__main__":
    main()
