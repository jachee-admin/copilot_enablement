#!/usr/bin/env python3
"""
Prompt Coach — Streamlit UI
Run:  streamlit run tools/ui_streamlit.py
"""

from __future__ import annotations
import os
import json
import textwrap
import streamlit as st

# Load your package
from coach.scorer import score_and_improve

# (Optional) auto-load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

st.set_page_config(
    page_title="Prompt Coach (AI Prompt Optimizer)",
    layout="wide",
)

# --- Sidebar controls ---------------------------------------------------------
st.sidebar.title("Prompt Coach")
st.sidebar.caption("AI Prompt Optimizer")

# API key management (lets you override without touching your shell)
api_key_input = st.sidebar.text_input(
    "OPENAI_API_KEY",
    value=os.environ.get("OPENAI_API_KEY", ""),
    type="password",
    help="Your OpenAI API key (kept in this session only).",
)
if api_key_input:
    os.environ["OPENAI_API_KEY"] = api_key_input

model = st.sidebar.text_input(
    "Model (env: PROMPT_COACH_MODEL)",
    value=os.environ.get("PROMPT_COACH_MODEL", "gpt-4o-mini"),
    help="Override the model used by Prompt Coach (e.g., gpt-4o, gpt-4o-mini).",
)
if model:
    os.environ["PROMPT_COACH_MODEL"] = model

timeout_s = st.sidebar.number_input(
    "Timeout (seconds)",
    min_value=5,
    max_value=120,
    value=int(float(os.environ.get("PROMPT_COACH_TIMEOUT", "30"))),
    help="Per-request timeout when calling the model.",
)
os.environ["PROMPT_COACH_TIMEOUT"] = str(timeout_s)

st.sidebar.markdown("---")
st.sidebar.info(
    "Tip: Paste any prompt (Copilot/ChatGPT). "
    "Click **Evaluate** to get a score, an improved version, a diff, and verification steps."
)

# --- Main body ----------------------------------------------------------------
#st.title("🧠 Prompt Coach — AI Prompt Optimizer")
st.title("Prompt Coach — AI Prompt Optimizer")
st.write(
    "Score and improve prompts using your house style "
    "(Role → Context → Task → Format → Guardrails → Acceptance)."
)

DEFAULT_PROMPT = textwrap.dedent("""\
    write postgres stuff
""")

prompt = st.text_area(
    "Paste your prompt",
    height=220,
    value=DEFAULT_PROMPT,
    placeholder="Paste or write any prompt here…",
    key="prompt_text",
)

cols = st.columns([1, 1, 2])
with cols[0]:
    run_btn = st.button("✨ Evaluate", type="primary")
with cols[1]:
    clear_btn = st.button("Clear")

# Clear: reset the bound key, then rerun
if clear_btn:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- Evaluate -----------------------------------------------------------------
if run_btn:
    text = prompt.strip()
    if not text:
        st.warning("Please paste a prompt first.")
    else:
        try:
            with st.spinner("Scoring and improving…"):
                result = score_and_improve(text)

            # Topline metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Final Score", result.get("final_score", 0))
            m2.metric("Local (Heuristics)", result.get("local_score", 0))
            m3.metric("Model Judgement", result.get("model_score", 0))
            usage = result.get("usage", {}) or {}
            m4.metric("Tokens (total)", usage.get("total_tokens", 0))

            # Improved prompt (copyable)
            with st.expander("✅ Improved Prompt", expanded=True):
                improved_text = result.get("improved", "")
                # Add extra line breaks before section headers for better readability
                sections = ["[ROLE SETUP]", "[CONTEXT]", "[TASK]", "[FORMAT CONTRACT]", "[GUARDRAILS]", "[ACCEPTANCE]"]
                formatted_text = improved_text
                for section in sections:
                    formatted_text = formatted_text.replace(section, f"\n{section}")
                # Remove leading newline if it exists
                formatted_text = formatted_text.lstrip("\n")
                st.code(formatted_text, language=None)

            # Before/After diff
            with st.expander("🧾 Before/After Diff"):
                diff_text = result.get("diff", "")
                if diff_text:
                    # Process the diff to make it more readable
                    lines = diff_text.split('\n')
                    formatted_diff = []

                    for line in lines:
                        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                            formatted_diff.append(line)
                        elif line.startswith('-'):
                            # Split long removed lines into chunks for better readability
                            content = line[1:]  # Remove the '-' prefix
                            if len(content) > 80:
                                words = content.split()
                                chunks = []
                                current_chunk = []
                                current_length = 0

                                for word in words:
                                    if current_length + len(word) + 1 > 80 and current_chunk:
                                        chunks.append('-' + ' '.join(current_chunk))
                                        current_chunk = [word]
                                        current_length = len(word)
                                    else:
                                        current_chunk.append(word)
                                        current_length += len(word) + 1

                                if current_chunk:
                                    chunks.append('-' + ' '.join(current_chunk))
                                formatted_diff.extend(chunks)
                            else:
                                formatted_diff.append(line)
                        elif line.startswith('+'):
                            # Split long added lines into chunks for better readability
                            content = line[1:]  # Remove the '+' prefix
                            if len(content) > 80:
                                words = content.split()
                                chunks = []
                                current_chunk = []
                                current_length = 0

                                for word in words:
                                    if current_length + len(word) + 1 > 80 and current_chunk:
                                        chunks.append('+' + ' '.join(current_chunk))
                                        current_chunk = [word]
                                        current_length = len(word)
                                    else:
                                        current_chunk.append(word)
                                        current_length += len(word) + 1

                                if current_chunk:
                                    chunks.append('+' + ' '.join(current_chunk))
                                formatted_diff.extend(chunks)
                            else:
                                formatted_diff.append(line)
                        else:
                            formatted_diff.append(line)

                    st.code('\n'.join(formatted_diff), language="diff")
                else:
                    st.write("No changes detected")

            # Scorecard
            with st.expander("📊 Scorecard"):
                st.json(result.get("scorecard", {}))

            # Verification commands
            verification = result.get("verification", []) or []
            if verification:
                with st.expander("🔍 Verification Steps"):
                    st.write("\n".join(f"- `{cmd}`" for cmd in verification))

            # Notes
            notes = result.get("notes", []) or []
            if notes:
                with st.expander("📝 Notes"):
                    st.write("\n".join(f"- {n}" for n in notes))

            # Raw JSON (debug)
            with st.expander("🧩 Raw JSON (debug)"):
                st.code(json.dumps(result, indent=2, ensure_ascii=False), language="json")

        except Exception as e:
            st.error(f"Error during evaluation: {e}")
            st.stop()

# Footer
st.markdown("---")
st.caption(
    "Prompt Coach uses your repo’s Common Prompt Patterns and a scoring rubric "
    "(Clarity, Context, Constraints, Format, Guardrails, Acceptance). "
    "Models and timeouts are configurable via sidebar or environment."
)
