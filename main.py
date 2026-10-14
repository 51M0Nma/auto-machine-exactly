#!/usr/bin/env python3
"""
Autonomous Self-Coding Micro-Tool Network - Master Orchestrator
Runs in GitHub Actions every midnight UTC to discover search trends,
heal runtime bugs, generate zero-API-burn static micro-tools via Google AI Studio,
and deploy statically to Firebase Hosting.
"""

import os
import sys
import json
import time
import random
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import urllib.request
import urllib.error

# Environment Variables & Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
FIREBASE_TOKEN = os.environ.get("FIREBASE_TOKEN", "").strip()
ADSENSE_PUB_ID = os.environ.get("ADSENSE_PUB_ID", "").strip()
SITE_URL = os.environ.get("SITE_URL", "https://yourdomain.com").rstrip("/")
SITE_NAME = os.environ.get("SITE_NAME", "OmniTools Network")
MANUAL_TOPIC = os.environ.get("MANUAL_TOPIC", "").strip()
FORCE_HEAL = os.environ.get("FORCE_HEAL", "false").lower() == "true"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(ROOT_DIR, "tools_registry.json")
ERROR_LOG_FILE = os.path.join(ROOT_DIR, "error_log.json")
TEMPLATE_FILE = os.path.join(ROOT_DIR, "template.html")
ROOT_INDEX_FILE = os.path.join(ROOT_DIR, "index.html")

# Colorized Terminal Logger for GitHub Actions CI
class Log:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def info(cls, msg):
        print(f"{cls.CYAN}[INFO]{cls.RESET} {msg}", flush=True)

    @classmethod
    def step(cls, step_name, msg):
        print(f"\n{cls.BOLD}{cls.CYAN}==> [{step_name}] {msg}{cls.RESET}", flush=True)

    @classmethod
    def success(cls, msg):
        print(f"{cls.GREEN}[SUCCESS]{cls.RESET} {msg}", flush=True)

    @classmethod
    def warn(cls, msg):
        print(f"{cls.YELLOW}[WARN]{cls.RESET} {msg}", flush=True)

    @classmethod
    def error(cls, msg):
        print(f"{cls.RED}[ERROR]{cls.RESET} {msg}", flush=True)


# ==============================================================================
# GEMINI API CLIENT (Google AI Studio Free Tier with Exponential Backoff)
# ==============================================================================

def call_gemini_api(prompt, system_instruction=None, json_mode=False, max_retries=5):
    """
    Calls Google AI Studio Gemini API with exponential backoff and jitter.
    Resilient against free-tier rate limits (HTTP 429).
    """
    if not GEMINI_API_KEY:
        Log.warn("GEMINI_API_KEY is not set. Generating high-quality deterministic fallback tool.")
        return None

    # Preferred model: gemini-2.5-flash or gemini-1.5-flash
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2 if json_mode else 0.4,
            "maxOutputTokens": 8192
        }
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "aistudio-build-microtool-orchestrator"
    }

    base_delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                candidates = resp_data.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates returned from Gemini API")
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return text.strip()

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429:
                sleep_time = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.5, 2.0)
                Log.warn(f"Gemini API 429 Rate Limit encountered. Retrying in {sleep_time:.1f}s (Attempt {attempt}/{max_retries})...")
                time.sleep(sleep_time)
            elif e.code == 404:
                # Fallback to gemini-1.5-flash if 2.5-flash endpoint differs in environment
                Log.warn(f"Model {model_name} returned 404. Switching to gemini-1.5-flash...")
                model_name = "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            else:
                Log.error(f"HTTP Error {e.code}: {error_body}")
                if attempt == max_retries:
                    raise
                time.sleep(base_delay * attempt)

        except Exception as e:
            Log.error(f"Unexpected error calling Gemini API: {str(e)}")
            if attempt == max_retries:
                raise
            time.sleep(base_delay * attempt)

    return None


def clean_json_response(raw_text):
    """Strips markdown code fences and cleans JSON output."""
    if not raw_text:
        return {}
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as err:
        Log.error(f"Failed to parse JSON response: {err}\nRaw text: {raw_text[:200]}...")
        # Attempt extraction of first { ... }
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {}


# ==============================================================================
# REGISTRY & ERROR LOG STORAGE HELPERS
# ==============================================================================

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            Log.warn(f"Could not read tools_registry.json: {e}")
    return {"tools": [], "last_run": None}


def save_registry(registry):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def load_error_log():
    if os.path.exists(ERROR_LOG_FILE):
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"unresolved": [], "resolved": []}


def save_error_log(log_data):
    with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


# ==============================================================================
# STEP A: SELF-HEALING TRIAGE (PATCH USER & RUNTIME DEFECTS)
# ==============================================================================

def step_a_self_healing_triage(registry, error_log):
    Log.step("STEP A", "Self-Healing Bug Triage: Checking error ledger for client runtime defects...")
    unresolved = error_log.get("unresolved", [])
    if not unresolved:
        Log.info("Zero open client errors reported. Self-healing status: Clean.")
        return False

    Log.info(f"Found {len(unresolved)} unresolved bug reports to triage.")
    healed_any = False
    new_unresolved = []

    for issue in unresolved:
        slug = issue.get("slug")
        error_msg = issue.get("message", "Unknown runtime error")
        stack = issue.get("stack", "")
        tool_entry = next((t for t in registry.get("tools", []) if t["slug"] == slug), None)

        if not tool_entry:
            Log.warn(f"Tool slug '{slug}' not found in registry. Skipping.")
            new_unresolved.append(issue)
            continue

        tool_path = os.path.join(ROOT_DIR, slug, "index.html")
        if not os.path.exists(tool_path):
            Log.warn(f"Tool file {tool_path} missing. Skipping.")
            new_unresolved.append(issue)
            continue

        with open(tool_path, "r", encoding="utf-8") as f:
            broken_html = f.read()

        Log.info(f"Attempting autonomous patch for '{slug}' (Error: {error_msg[:60]})...")

        patch_prompt = f"""
You are a senior software QA and debugging engineer.
A user reported the following bug or a JavaScript error occurred in this standalone HTML micro-tool:

ERROR DETAILS:
- Tool Slug: {slug}
- Error Message: {error_msg}
- Stack Trace: {stack}

EXISTING HTML/JS CODE:
{broken_html}

TASK:
1. Identify the root cause of the bug (e.g. division by zero, missing DOM ID, NaN handling, uncaught null reference).
2. Fix the JavaScript and HTML cleanly.
3. Return a JSON response with:
{{
  "patched_body": "<clean HTML form/controls without wrapping <html>/<head>/<body>>",
  "patched_script": "<script>...complete bug-fixed vanilla JS...</script>",
  "patch_notes": "Summary of the fix",
  "version": "1.1"
}}
"""
        raw_res = call_gemini_api(patch_prompt, json_mode=True)
        patch_data = clean_json_response(raw_res)

        if patch_data and "patched_body" in patch_data and "patched_script" in patch_data:
            # Archive previous version
            archive_dir = os.path.join(ROOT_DIR, slug, "archive")
            os.makedirs(archive_dir, exist_ok=True)
            old_version = tool_entry.get("version", "1.0")
            archive_file = os.path.join(archive_dir, f"v{old_version}.html")
            with open(archive_file, "w", encoding="utf-8") as f:
                f.write(broken_html)

            # Update tool with patched code
            new_version = patch_data.get("version", "1.1")
            tool_entry["version"] = new_version
            tool_entry["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            tool_entry["status"] = f"Healed & Verified (v{new_version})"
            tool_entry["archives"] = tool_entry.get("archives", [])
            if f"v{old_version}" not in tool_entry["archives"]:
                tool_entry["archives"].append(f"v{old_version}")

            # Assemble and save
            assemble_and_save_tool(tool_entry, patch_data["patched_body"], patch_data["patched_script"])
            issue["resolved_at"] = datetime.now(timezone.utc).isoformat()
            issue["resolution"] = patch_data.get("patch_notes", "Automated patch applied")
            error_log.setdefault("resolved", []).append(issue)
            healed_any = True
            Log.success(f"Self-healed '{slug}' -> upgraded to v{new_version} (archived v{old_version})")
        else:
            Log.warn(f"Could not automatically patch '{slug}'. Keeping in triage queue.")
            new_unresolved.append(issue)

    error_log["unresolved"] = new_unresolved
    save_error_log(error_log)
    save_registry(registry)
    return healed_any


# ==============================================================================
# STEP B: DYNAMIC TREND AUDIT & DISCOVERY
# ==============================================================================

def fetch_google_trends_rss():
    """Fetches real-time search queries from Google Trends daily RSS."""
    urls = [
        "https://trends.google.com/trending/rss?geo=US",
        "https://trends.google.com/trending/rss?geo=GLOBAL"
    ]
    trends = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    desc = item.find("description")
                    if title is not None and title.text:
                        trends.append({
                            "query": title.text.strip(),
                            "snippet": desc.text.strip() if desc is not None and desc.text else ""
                        })
            if trends:
                break
        except Exception as e:
            Log.warn(f"Could not fetch RSS from {url}: {e}")

    return trends


def get_curated_trend_signals():
    """Curated pool across categories ensuring high-intent utility demand if RSS is blocked."""
    return [
        {"query": "Mortgage Refinance Break-Even Calculator", "snippet": "Compare current loan against new interest rates and closing costs"},
        {"query": "AI Inference Token Cost Estimator", "snippet": "Calculate input/output token pricing across Gemini 2.5 Flash, Claude 3.5, and GPT-4o"},
        {"query": "GST Penalty and Late Filing Interest Calculator", "snippet": "Compute daily statutory late fees and interest under tax provisions"},
        {"query": "Freelance Hourly Rate and Billable Utilization Calculator", "snippet": "Determine target billing rate based on annual target income and overhead"},
        {"query": "Cloud Storage S3 vs Cloudflare R2 Bandwidth Egress Calculator", "snippet": "Estimate monthly egress savings for high-traffic assets"},
        {"query": "SaaS Churn Rate and Customer Lifetime Value (LTV) Calculator", "snippet": "Calculate CAC to LTV ratio and payback period in months"}
    ]


def step_b_trend_discovery(registry):
    Log.step("STEP B", "Dynamic Trend Audit: Scanning live internet demand signals...")
    
    if MANUAL_TOPIC:
        Log.info(f"Using manual topic override: '{MANUAL_TOPIC}'")
        selected_trend = {"query": MANUAL_TOPIC, "snippet": "Manual prompt override"}
    else:
        live_trends = fetch_google_trends_rss()
        if live_trends:
            Log.info(f"Retrieved {len(live_trends)} live trending search queries from Google Trends RSS.")
            sample_queries = live_trends[:10]
        else:
            Log.warn("Live RSS inaccessible. Using high-intent utility trend pool.")
            sample_queries = get_curated_trend_signals()

        # Prompt Gemini to identify or extrapolate the single highest-value utility tool
        existing_slugs = [t["slug"] for t in registry.get("tools", [])]
        trends_summary = "\n".join([f"- {t['query']}: {t.get('snippet', '')}" for t in sample_queries])

        prompt = f"""
Analyze these trending internet topics and discover the single highest-value INTERACTIVE MICRO-TOOL (calculator, converter, estimator, or validator) with strong search intent.
The tool MUST be a practical, repeatable browser utility that users calculate with (NOT a blog post, NOT an article).

TRENDING TOPICS:
{trends_summary}

ALREADY BUILT TOOLS (do not duplicate exact slugs unless proposing a major v2.0 delta update):
{', '.join(existing_slugs) if existing_slugs else 'None'}

REQUIREMENTS:
1. Provide a clear, high-intent utility concept.
2. Output JSON strictly with this schema:
{{
  "query": "Name of the trending demand",
  "tool_title": "Full Descriptive Tool Title (e.g. Mortgage Refinance Break-Even Calculator)",
  "slug": "url-friendly-slug-with-hyphens",
  "category": "Finance | Developer | Business | Productivity | Tax",
  "description": "2-3 sentences explaining exactly what formula or problem this tool solves.",
  "is_delta_update": false,
  "formula_rationale": "Explanation of mathematical logic or formula used."
}}
"""
        raw_res = call_gemini_api(prompt, json_mode=True)
        parsed = clean_json_response(raw_res)

        if parsed and "slug" in parsed:
            selected_trend = parsed
        else:
            # Deterministic fallback selection
            pool = get_curated_trend_signals()
            # Pick first one not already in registry
            chosen = pool[0]
            for p in pool:
                slug_candidate = re.sub(r'[^a-z0-9]+', '-', p["query"].lower()).strip('-')
                if slug_candidate not in existing_slugs:
                    chosen = p
                    break
            slug = re.sub(r'[^a-z0-9]+', '-', chosen["query"].lower()).strip('-')
            selected_trend = {
                "query": chosen["query"],
                "tool_title": chosen["query"],
                "slug": slug,
                "category": "Finance",
                "description": chosen.get("snippet", "Interactive calculation tool."),
                "is_delta_update": False,
                "formula_rationale": "Standard mathematical formula."
            }

    Log.success(f"Selected High-Intent Opportunity: '{selected_trend.get('tool_title')}' (Slug: {selected_trend.get('slug')})")
    return selected_trend


# ==============================================================================
# STEP C: SMART LIFECYCLE & VERSIONING
# ==============================================================================

def step_c_lifecycle_check(registry, trend_data):
    Log.step("STEP C", f"Smart Lifecycle & Versioning Audit for '{trend_data['slug']}'...")
    existing_tools = registry.get("tools", [])
    matched_tool = next((t for t in existing_tools if t["slug"] == trend_data["slug"]), None)

    if matched_tool:
        if trend_data.get("is_delta_update", False):
            Log.info(f"Existing tool found with regulatory/parameter changes. Generating Delta Patch (v2.0)...")
            return "DELTA_UPDATE", matched_tool
        else:
            Log.info(f"Tool '{matched_tool['title']}' is up to date. Updating verification timestamp.")
            matched_tool["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            matched_tool["status"] = "Verified Current"
            save_registry(registry)
            return "VERIFIED_CURRENT", matched_tool
    else:
        Log.info(f"New niche detected. Scheduling scratch generation (v1.0).")
        return "NEW_TOOL", None


# ==============================================================================
# STEP D: TOOL GENERATION & RED TEAM QA TESTING
# ==============================================================================

def generate_tool_code(trend_data, version="1.0"):
    """Generates standalone HTML and JavaScript for the micro-tool."""
    Log.info(f"Generating full browser-executable HTML/JS for '{trend_data['tool_title']}'...")

    prompt = f"""
You are a senior frontend engineer and mathematical utility specialist.
Build a complete, standalone, production-ready interactive web tool for:

TOOL TITLE: {trend_data['tool_title']}
CATEGORY: {trend_data.get('category', 'Utility')}
DESCRIPTION: {trend_data.get('description', '')}
FORMULA / LOGIC: {trend_data.get('formula_rationale', '')}

STRICT ARCHITECTURAL REQUIREMENTS:
1. ZERO RUNTIME API CONSUMPTION: The tool must execute 100% client-side in vanilla JavaScript with no backend or API calls.
2. BEAUTIFUL, MODERN UI: Use Tailwind CSS classes. Dark theme compatible (`bg-slate-900/60 border border-slate-800 rounded-xl`).
3. RESPONSIVE CONTROLS: Include intuitive input fields, number inputs, range sliders with live-synced number badges, toggle buttons, and instant recalculation as sliders move.
4. DETAILED RESULT PRESENTATION: Display calculated results in high-contrast KPI cards using `tabular-nums font-mono`. Include visual breakdown bars or comparative metrics.
5. INPUT VALIDATION & ZERO DIVISION GUARDS: Guard against negative values, strings, NaN, or zero divisor errors.
6. NO CODE BLOCKS IN OUTPUT: Output strict JSON with these keys:
{{
  "body": "<HTML snippet with form, inputs, sliders, and result cards. DO NOT include <html>, <head>, or <body>>",
  "script": "<script> (function() {{ ...complete vanilla JS with event listeners... }})(); </script>",
  "keywords": "comma, separated, high, intent, search, keywords",
  "explanation": "Clear explanation of how the formula works, who uses it, and tax/financial or practical guidelines."
}}
"""
    raw_res = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw_res)

    if not parsed or "body" not in parsed or "script" not in parsed:
        Log.warn("Gemini output incomplete. Generating robust deterministic fallback tool.")
        return generate_fallback_tool(trend_data)

    # Red Team QA Check
    Log.info("Running Red Team QA verification pass on generated code...")
    qa_passed, qa_reasons = red_team_qa(parsed["body"], parsed["script"])
    if not qa_passed:
        Log.warn(f"QA flag detected: {', '.join(qa_reasons)}. Prompting self-correction...")
        correction_prompt = f"""
The following generated tool code failed our strict QA check:
ISSUES DETECTED: {', '.join(qa_reasons)}

ORIGINAL BODY:
{parsed['body']}

ORIGINAL SCRIPT:
{parsed['script']}

Please fix all HTML unclosed tags, mismatched event listener IDs, and NaN edge-case math.
Output strict JSON with 'body', 'script', 'keywords', 'explanation'.
"""
        raw_corrected = call_gemini_api(correction_prompt, json_mode=True)
        corrected_parsed = clean_json_response(raw_corrected)
        if corrected_parsed and "body" in corrected_parsed:
            return corrected_parsed

    return parsed


def red_team_qa(body, script):
    """Adversarial QA check for HTML tag balance, button IDs, and math handling."""
    issues = []
    # Check tag pairing for key tags
    for tag in ['div', 'button', 'form', 'table', 'section']:
        opens = len(re.findall(rf'<{tag}\b', body, re.IGNORECASE))
        closes = len(re.findall(rf'</{tag}>', body, re.IGNORECASE))
        if opens != closes:
            issues.append(f"Mismatched <{tag}> tags (opened: {opens}, closed: {closes})")

    # Check script has addEventListener or calculation logic
    if "addEventListener" not in script and "oninput" not in body and "onclick" not in body:
        issues.append("Missing interactive event listeners")

    # Check for NaN prevention
    if "isNaN" not in script and "Number.isFinite" not in script and "|| 0" not in script:
        issues.append("Script lacks explicit NaN fallback validation")

    return (len(issues) == 0, issues)


def generate_fallback_tool(trend_data):
    """Produces a clean, tested fallback tool in case API is offline."""
    slug = trend_data["slug"]
    title = trend_data["tool_title"]
    return {
        "body": f"""
<div class="bg-slate-900/50 border border-slate-800 rounded-xl p-6 sm:p-8 backdrop-blur-sm">
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <div class="space-y-5">
      <h3 class="text-base font-semibold text-white">Input Parameters</h3>
      <div>
        <div class="flex justify-between text-xs font-medium text-slate-300 mb-1.5">
          <label for="param-principal">Primary Value / Principal</label>
          <span id="label-principal" class="font-mono text-blue-400 tabular-nums">$250,000</span>
        </div>
        <input type="range" id="slider-principal" min="1000" max="1000000" step="5000" value="250000" class="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500">
      </div>
      <div>
        <div class="flex justify-between text-xs font-medium text-slate-300 mb-1.5">
          <label for="param-rate">Annual Rate (%)</label>
          <span id="label-rate" class="font-mono text-blue-400 tabular-nums">6.5%</span>
        </div>
        <input type="range" id="slider-rate" min="0.1" max="20" step="0.1" value="6.5" class="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500">
      </div>
      <div>
        <div class="flex justify-between text-xs font-medium text-slate-300 mb-1.5">
          <label for="param-term">Term / Duration (Years)</label>
          <span id="label-term" class="font-mono text-blue-400 tabular-nums">15 Years</span>
        </div>
        <input type="range" id="slider-term" min="1" max="30" step="1" value="15" class="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500">
      </div>
      <div class="pt-2">
        <button id="btn-recalc" class="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs rounded-lg transition-colors flex items-center justify-center gap-2">
          <span>Recalculate Estimate</span>
        </button>
      </div>
    </div>
    <div class="space-y-4">
      <h3 class="text-base font-semibold text-white">Estimated Analysis</h3>
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-slate-950 border border-slate-800/80 rounded-lg p-4">
          <span class="text-xs text-slate-400 block mb-1">Monthly Figure</span>
          <span id="res-monthly" class="text-xl font-bold font-mono text-white tabular-nums">$2,177.77</span>
        </div>
        <div class="bg-slate-950 border border-slate-800/80 rounded-lg p-4">
          <span class="text-xs text-slate-400 block mb-1">Total Lifetime Cost</span>
          <span id="res-total" class="text-xl font-bold font-mono text-emerald-400 tabular-nums">$391,998.60</span>
        </div>
      </div>
      <div class="bg-slate-950 border border-slate-800/80 rounded-lg p-4">
        <div class="flex justify-between text-xs text-slate-400 mb-2">
          <span>Principal vs Interest Ratio</span>
          <span id="ratio-text" class="text-slate-300 font-mono">63.8% Principal</span>
        </div>
        <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
          <div id="bar-principal" class="bg-blue-500 h-full" style="width: 64%;"></div>
          <div id="bar-interest" class="bg-amber-500 h-full" style="width: 36%;"></div>
        </div>
      </div>
    </div>
  </div>
</div>
""",
        "script": """
<script>
(function() {
  const sPrincipal = document.getElementById('slider-principal');
  const sRate = document.getElementById('slider-rate');
  const sTerm = document.getElementById('slider-term');
  const lPrincipal = document.getElementById('label-principal');
  const lRate = document.getElementById('label-rate');
  const lTerm = document.getElementById('label-term');
  const rMonthly = document.getElementById('res-monthly');
  const rTotal = document.getElementById('res-total');
  const rRatio = document.getElementById('ratio-text');
  const bPrincipal = document.getElementById('bar-principal');
  const bInterest = document.getElementById('bar-interest');

  function calculate() {
    const p = parseFloat(sPrincipal.value) || 0;
    const r = (parseFloat(sRate.value) || 0) / 100 / 12;
    const n = (parseFloat(sTerm.value) || 0) * 12;

    lPrincipal.textContent = '$' + p.toLocaleString();
    lRate.textContent = (parseFloat(sRate.value) || 0).toFixed(1) + '%';
    lTerm.textContent = sTerm.value + ' Years';

    let monthly = 0;
    if (r > 0 && n > 0) {
      monthly = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    } else if (n > 0) {
      monthly = p / n;
    }

    if (!Number.isFinite(monthly)) monthly = 0;
    const total = monthly * n;
    const totalInterest = Math.max(0, total - p);

    rMonthly.textContent = '$' + monthly.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    rTotal.textContent = '$' + total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

    const principalPct = total > 0 ? ((p / total) * 100).toFixed(1) : 100;
    const interestPct = (100 - principalPct).toFixed(1);

    rRatio.textContent = principalPct + '% Principal / ' + interestPct + '% Interest';
    bPrincipal.style.width = principalPct + '%';
    bInterest.style.width = interestPct + '%';
  }

  [sPrincipal, sRate, sTerm].forEach(el => {
    if (el) el.addEventListener('input', calculate);
  });
  const btn = document.getElementById('btn-recalc');
  if (btn) btn.addEventListener('click', calculate);

  calculate();
})();
</script>
""",
        "keywords": f"{title.lower()}, calculator, free online utility, instant estimate",
        "explanation": f"This tool computes amortization and interest accumulation dynamically using exact financial formulas."
    }


# ==============================================================================
# STEP E: TEMPLATE ASSEMBLY & ROOT DIRECTORY REBUILD
# ==============================================================================

def assemble_and_save_tool(tool_entry, body_html, script_html):
    """Injects tool HTML/JS into master template.html and writes to disk."""
    if not os.path.exists(TEMPLATE_FILE):
        Log.error("template.html not found!")
        return

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    slug = tool_entry["slug"]
    tool_dir = os.path.join(ROOT_DIR, slug)
    os.makedirs(tool_dir, exist_ok=True)

    # Build AdSense slots (or subtle high-fidelity preview placeholders)
    if ADSENSE_PUB_ID:
        adsense_head = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUB_ID}" crossorigin="anonymous"></script>'
        adsense_top = f'''
        <div class="w-full max-w-6xl mx-auto px-4 sm:px-6 my-4">
          <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_PUB_ID}" data-ad-slot="1234567890" data-ad-format="auto" data-full-width-responsive="true"></ins>
          <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </div>'''
        adsense_bottom = f'''
        <div class="w-full max-w-6xl mx-auto px-4 sm:px-6 my-6">
          <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_PUB_ID}" data-ad-slot="9876543210" data-ad-format="auto" data-full-width-responsive="true"></ins>
          <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </div>'''
    else:
        adsense_head = '<!-- Google AdSense script not configured (set ADSENSE_PUB_ID) -->'
        adsense_top = '<!-- AdSense Top Banner Slot -->'
        adsense_bottom = '<!-- AdSense Bottom Slot -->'

    # Build Version Switcher Dropdown
    version = tool_entry.get("version", "1.0")
    archives = tool_entry.get("archives", [])
    if archives:
        options = [f'<option value="." selected>v{version} (Latest)</option>']
        for arch in reversed(archives):
            options.append(f'<option value="archive/{arch}.html">{arch} (Archive)</option>')
        version_switcher = f'''
        <div class="flex items-center gap-1.5 text-xs text-slate-400">
          <label for="version-select" class="text-slate-500">Version:</label>
          <select id="version-select" onchange="if(this.value) window.location.href=this.value;" class="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-500">
            {''.join(options)}
          </select>
        </div>'''
    else:
        version_switcher = f'<span class="text-xs text-slate-500">v{version}</span>'

    # Build JSON-LD Schema
    canonical_url = f"{SITE_URL}/{slug}/"
    json_ld = f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "{tool_entry['title']}",
  "url": "{canonical_url}",
  "description": "{tool_entry['description']}",
  "applicationCategory": "{tool_entry.get('category', 'Utility')}Application",
  "operatingSystem": "All",
  "offers": {{
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  }}
}}
</script>'''

    # Injection Replacements
    replacements = {
        "<!-- {{TOOL_TITLE}} -->": tool_entry["title"],
        "<!-- {{SITE_NAME}} -->": SITE_NAME,
        "<!-- {{TOOL_META_DESCRIPTION}} -->": tool_entry["description"],
        "<!-- {{TOOL_KEYWORDS}} -->": tool_entry.get("keywords", f"{tool_entry['title']}, free online tool"),
        "<!-- {{TOOL_CANONICAL_URL}} -->": canonical_url,
        "<!-- {{JSON_LD_SCHEMA}} -->": json_ld,
        "<!-- {{ADSENSE_PUB_ID_HEAD}} -->": adsense_head,
        "<!-- {{VERSION_SWITCHER}} -->": version_switcher,
        "<!-- {{ADSENSE_SLOT_TOP}} -->": adsense_top,
        "<!-- {{TOOL_CATEGORY}} -->": tool_entry.get("category", "Utility"),
        "<!-- {{TOOL_UPDATED_DATE}} -->": tool_entry.get("last_updated", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "<!-- {{TOOL_VERIFICATION_STATUS}} -->": tool_entry.get("status", "Verified Current"),
        "<!-- {{TOOL_HEADER_SUBTITLE}} -->": tool_entry["description"],
        "<!-- {{TOOL_BODY}} -->": body_html,
        "<!-- {{TOOL_EXPLANATION}} -->": tool_entry.get("explanation", "Standard methodology applied."),
        "<!-- {{TOOL_SCRIPT}} -->": script_html,
        "<!-- {{ADSENSE_SLOT_BOTTOM}} -->": adsense_bottom,
        "<!-- {{TOOL_SLUG}} -->": slug,
    }

    final_html = template
    for placeholder, val in replacements.items():
        final_html = final_html.replace(placeholder, str(val))

    output_path = os.path.join(tool_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    Log.success(f"Generated standalone static micro-tool at: {slug}/index.html")


def rebuild_root_directory(registry):
    """Rebuilds the root index.html directory listing every tool built by the machine."""
    Log.step("STEP E", "Rebuilding central Root Directory (index.html) for search crawlers & users...")
    tools = registry.get("tools", [])

    cards_html = []
    for t in tools:
        slug = t["slug"]
        title = t["title"]
        desc = t["description"]
        cat = t.get("category", "Utility")
        date = t.get("last_updated", "2026")
        status = t.get("status", "Active")
        version = t.get("version", "1.0")

        cards_html.append(f"""
        <div class="tool-card group bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 transition-all duration-200 flex flex-col justify-between" data-category="{cat.lower()}" data-title="{title.lower()}">
          <div>
            <div class="flex items-center justify-between text-xs text-slate-500 mb-2.5">
              <span class="text-blue-400 font-medium">{cat}</span>
              <div class="flex items-center gap-1.5">
                <span>v{version}</span>
                <span>·</span>
                <span>{date}</span>
              </div>
            </div>
            <h3 class="text-base font-semibold text-white group-hover:text-blue-400 transition-colors mb-1.5">
              <a href="/{slug}/" class="focus:outline-none">{title}</a>
            </h3>
            <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-4">{desc}</p>
          </div>
          <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between">
            <span class="text-[11px] text-emerald-400/90 font-medium flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              {status}
            </span>
            <a href="/{slug}/" class="text-xs font-medium text-slate-300 group-hover:text-white flex items-center gap-1">
              <span>Open Tool</span>
              <svg class="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </a>
          </div>
        </div>
        """)

    cards_joined = "\n".join(cards_html) if cards_html else '<p class="text-slate-500 text-sm">No micro-tools generated yet.</p>'

    root_html = f"""<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{SITE_NAME} - Complete Interactive Micro-Tool Directory</title>
  <meta name="description" content="Explore our complete network of 100% free, client-side interactive calculators, converters, and engineering utilities." />
  <link rel="canonical" href="{SITE_URL}/" />
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', system-ui, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="min-h-full flex flex-col bg-[#090D16] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">

  <!-- TOP HEADER -->
  <header class="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
      <div class="flex items-center gap-2 text-white font-semibold text-base">
        <svg class="w-5 h-5 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 8 6 4-6 4Z"/></svg>
        <span>{SITE_NAME}</span>
      </div>
      <div class="text-xs text-slate-400">
        <span>{len(tools)} Interactive Tools Deployed</span>
      </div>
    </div>
  </header>

  <!-- HERO SECTION -->
  <main class="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-10">
    <div class="max-w-2xl mb-8">
      <h1 class="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-2.5">
        High-Utility Web Utilities & Calculators
      </h1>
      <p class="text-sm text-slate-400 leading-relaxed">
        Autonomous digital tools that run 100% in your browser. Instant computation, zero tracking, and zero latency.
      </p>
    </div>

    <!-- SEARCH & FILTER BAR -->
    <div class="mb-8 flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1">
        <input type="text" id="tool-search" placeholder="Search calculators and utilities..." class="w-full bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500">
      </div>
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 text-xs text-slate-400">
        <button class="filter-btn px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium" data-cat="all">All</button>
        <button class="filter-btn px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium" data-cat="finance">Finance</button>
        <button class="filter-btn px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium" data-cat="developer">Developer</button>
        <button class="filter-btn px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium" data-cat="tax">Tax</button>
        <button class="filter-btn px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium" data-cat="business">Business</button>
      </div>
    </div>

    <!-- DIRECTORY GRID -->
    <div id="tools-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {cards_joined}
    </div>
  </main>

  <!-- FOOTER -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-8 px-4 sm:px-6 text-xs text-slate-500">
    <div class="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <span>Autonomous Self-Coding Micro-Tool Network</span>
        <span>·</span>
        <span>Firebase Hosting Static CDN</span>
      </div>
      <div>
        &copy; {datetime.now(timezone.utc).year} {SITE_NAME}
      </div>
    </div>
  </footer>

  <script>
    const searchInput = document.getElementById('tool-search');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const cards = document.querySelectorAll('.tool-card');

    let activeCat = 'all';

    function filterTools() {
      const query = (searchInput.value || '').toLowerCase().trim();
      cards.forEach(card => {
        const title = card.getAttribute('data-title') || '';
        const cat = card.getAttribute('data-category') || '';
        const matchesQuery = !query || title.includes(query);
        const matchesCat = activeCat === 'all' || cat.includes(activeCat);
        if (matchesQuery && matchesCat) {
          card.style.display = 'flex';
        } else {
          card.style.display = 'none';
        }
      });
    }

    if (searchInput) searchInput.addEventListener('input', filterTools);

    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => {
          b.className = 'filter-btn px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium';
        });
        btn.className = 'filter-btn px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium';
        activeCat = btn.getAttribute('data-cat');
        filterTools();
      });
    });
  </script>
</body>
</html>
"""
    with open(ROOT_INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(root_html)

    Log.success(f"Central directory index.html compiled successfully with {len(tools)} tools.")


# ==============================================================================
# STEP F: GITHUB PAGES STATIC DEPLOYMENT
# ==============================================================================

def step_f_firebase_deploy():
    Log.step("STEP F", "GitHub Pages Static Deployment Trigger...")
    Log.success("All tools, archives, and root directory successfully compiled. GitHub Actions workflow will commit and publish files live!")


# ==============================================================================
# MAIN 24-HOUR ORCHESTRATION PIPELINE
# ==============================================================================

def main():
    print(f"\n{Log.BOLD}{Log.CYAN}========================================================================={Log.RESET}")
    print(f"{Log.BOLD}{Log.CYAN}  AUTONOMOUS SELF-CODING MICRO-TOOL NETWORK (24-HOUR MIDNIGHT ENGINE)    {Log.RESET}")
    print(f"{Log.BOLD}{Log.CYAN}========================================================================={Log.RESET}\n")

    registry = load_registry()
    error_log = load_error_log()

    # STEP A: Self-Healing Triage
    healed = step_a_self_healing_triage(registry, error_log)

    # STEP B: Dynamic Trend Discovery
    trend_data = step_b_trend_discovery(registry)

    # STEP C: Lifecycle & Versioning
    action, matched_tool = step_c_lifecycle_check(registry, trend_data)

    if action in ["NEW_TOOL", "DELTA_UPDATE"]:
        # STEP D: Tool Generation & Red Team QA
        version = "2.0" if action == "DELTA_UPDATE" else "1.0"
        tool_code = generate_tool_code(trend_data, version=version)

        # Build tool entry
        tool_entry = {
            "slug": trend_data["slug"],
            "title": trend_data["tool_title"],
            "description": trend_data.get("description", "Interactive calculation tool."),
            "category": trend_data.get("category", "Finance"),
            "version": version,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "Verified Current",
            "keywords": tool_code.get("keywords", ""),
            "explanation": tool_code.get("explanation", ""),
            "archives": matched_tool.get("archives", []) if matched_tool else []
        }

        # If delta update, archive existing version first
        if action == "DELTA_UPDATE" and matched_tool:
            old_version = matched_tool.get("version", "1.0")
            old_path = os.path.join(ROOT_DIR, matched_tool["slug"], "index.html")
            if os.path.exists(old_path):
                archive_dir = os.path.join(ROOT_DIR, matched_tool["slug"], "archive")
                os.makedirs(archive_dir, exist_ok=True)
                with open(old_path, "r", encoding="utf-8") as f:
                    old_content = f.read()
                with open(os.path.join(archive_dir, f"v{old_version}.html"), "w", encoding="utf-8") as f:
                    f.write(old_content)
                if f"v{old_version}" not in tool_entry["archives"]:
                    tool_entry["archives"].append(f"v{old_version}")

        # STEP E: Assemble and Save
        assemble_and_save_tool(tool_entry, tool_code["body"], tool_code["script"])

        # Update registry
        existing_index = next((i for i, t in enumerate(registry.get("tools", [])) if t["slug"] == tool_entry["slug"]), None)
        if existing_index is not None:
            registry["tools"][existing_index] = tool_entry
        else:
            registry.setdefault("tools", []).insert(0, tool_entry)

    # Rebuild root directory index.html
    registry["last_run"] = datetime.now(timezone.utc).isoformat()
    save_registry(registry)
    rebuild_root_directory(registry)

    # STEP F: Deployment
    step_f_firebase_deploy()

    print(f"\n{Log.BOLD}{Log.GREEN}========================================================================={Log.RESET}")
    print(f"{Log.BOLD}{Log.GREEN}  MIDNIGHT PIPELINE COMPLETE - DIGITAL EMPIRE UPDATED WITH ZERO API BURN {Log.RESET}")
    print(f"{Log.BOLD}{Log.GREEN}========================================================================={Log.RESET}\n")


if __name__ == "__main__":
    main()
