"""
AI Coach: an agent that suggests the player's next guess.

It works in 4 steps:
1. PLAN:  work out which numbers are still possible from the guess history
          (plain Python, no AI).
2. ACT:   ask Gemini for a guess and a short reason, as JSON.
3. CHECK: reject broken replies and guesses outside the possible range,
          ask one more time, and fall back to the middle of the range if
          the AI still fails.
4. LOG:   write every step to logs/coach.log.

Guardrail: the secret number is never passed to this module, so it can
never be sent to the AI.
"""

import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_AI_TRIES = 2
LOG_FILE = Path(__file__).parent / "logs" / "coach.log"

logger = logging.getLogger("ai_coach")


def _setup_logging():
    """Send the coach's log lines to logs/coach.log (only set up once)."""
    if logger.handlers:
        return
    LOG_FILE.parent.mkdir(exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


_setup_logging()


# ---------------------------------------------------------------------------
# Step 1: PLAN
# ---------------------------------------------------------------------------

def get_possible_range(low, high, history, hints):
    """
    Work out which numbers can still be the secret.

    Args:
        low, high: the difficulty's range, for example 1 and 100.
        history: the player's valid guesses, for example [45, 20].
        hints: the hint shown for each guess, for example
            ["📉 Go LOWER! 🧊 Cold", "📈 Go HIGHER! 🌡️ Warm"].

    Returns:
        A tuple (low, high) with the numbers still possible, for example
        (21, 44).
    """
    for guess, hint in zip(history, hints):
        if "LOWER" in hint:
            high = min(high, guess - 1)
        elif "HIGHER" in hint:
            low = max(low, guess + 1)
    return low, high


# ---------------------------------------------------------------------------
# Step 2: ACT
# ---------------------------------------------------------------------------

# Few-shot examples: they teach the AI the answer format and the "pick the
# middle" strategy. The baseline prompt leaves them out.
FEW_SHOT_EXAMPLES = """Here are examples of good answers:

Example 1
Game range: 1 to 100. Guesses so far: none.
Numbers still possible: 1 to 100.
Answer: {"guess": 50, "reason": "50 is the middle of 1-100, so any hint cuts the options in half."}

Example 2
Game range: 1 to 100. Guesses so far: 50 -> Go LOWER.
Numbers still possible: 1 to 49.
Answer: {"guess": 25, "reason": "The secret is below 50, and 25 is the middle of 1-49."}

Example 3
Game range: 1 to 20. Guesses so far: 10 -> Go HIGHER, 15 -> Go LOWER.
Numbers still possible: 11 to 14.
Answer: {"guess": 12, "reason": "Only 11-14 are left, and 12 is in the middle."}
"""


def _describe_history(history, hints):
    """Turn the history into text like '45 -> Go LOWER, 20 -> Go HIGHER'."""
    if not history:
        return "none"
    parts = []
    for guess, hint in zip(history, hints):
        direction = "Go LOWER" if "LOWER" in hint else "Go HIGHER"
        parts.append(f"{guess} -> {direction}")
    return ", ".join(parts)


def build_prompt(low, high, history, hints, possible, few_shot=True):
    """
    Build the prompt sent to Gemini.

    The prompt only holds what the player can see (the game range, the
    guesses and their hints). It never holds the secret.

    Args:
        few_shot: True builds the specialized prompt: the strategy, the
            few-shot examples and the numbers still possible from the PLAN
            step. False builds the baseline prompt: only the game range and
            the guesses, so the AI has to work everything out alone.
    """
    lines = [
        "You are a coach in a number-guessing game.",
        "Suggest the player's next guess.",
        "",
    ]
    if few_shot:
        lines += [
            "Strategy: always guess the middle of the numbers still "
            "possible, so each hint removes half of them.",
            "",
            FEW_SHOT_EXAMPLES,
        ]
    lines += [
        "Now the real game:",
        f"Game range: {low} to {high}. "
        f"Guesses so far: {_describe_history(history, hints)}.",
    ]
    if few_shot:
        lines.append(
            f"Numbers still possible: {possible[0]} to {possible[1]}."
        )
    lines += [
        "",
        'Reply with only JSON like {"guess": <whole number>, '
        '"reason": "<one short sentence>"}.',
    ]
    return "\n".join(lines)


def ask_gemini(prompt):
    """
    Send the prompt to Gemini and return its reply text.

    Raises:
        RuntimeError: if GEMINI_API_KEY is missing.
        Any error from the Gemini library (no internet, quota, bad key).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (see README setup)")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Step 3: CHECK
# ---------------------------------------------------------------------------

def parse_reply(text):
    """
    Read the guess and reason out of the AI's reply.

    Returns:
        A tuple (guess, reason).

    Raises:
        ValueError: if the reply has no valid JSON, the guess is not a
            whole number, or the reason is missing.
    """
    match = re.search(r"\{.*?\}", text or "", re.DOTALL)
    if not match:
        raise ValueError("no JSON found in the reply")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise ValueError(f"broken JSON: {error}") from error

    guess = data.get("guess")
    reason = data.get("reason")
    if not isinstance(guess, int) or isinstance(guess, bool):
        raise ValueError(f"guess is not a whole number: {guess!r}")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason is missing")
    return guess, reason.strip()[:200]


# ---------------------------------------------------------------------------
# The agent: runs the 4 steps
# ---------------------------------------------------------------------------

def get_coach_advice(low, high, history, hints, few_shot=True,
                     ask_fn=ask_gemini):
    """
    Suggest the next guess.

    Args:
        low, high: the difficulty's range.
        history, hints: the valid guesses so far and their hints.
        few_shot: use the specialized prompt (True) or the baseline (False).
        ask_fn: the function that calls the AI. Tests pass a fake one.

    Returns:
        A dict with:
        - "guess": the suggested number.
        - "reason": a short explanation.
        - "source": "ai" if the AI's answer passed the checks, "fallback"
          if the code had to pick the middle of the range instead.
        - "possible": the (low, high) range still possible.
        - "trace": the list of steps, also written to logs/coach.log.
    """
    trace = []

    def log_step(message):
        trace.append(message)
        logger.info(message)

    mode = "few-shot" if few_shot else "baseline"
    log_step(f"START range={low}-{high} history={list(history)} mode={mode}")

    # Step 1: PLAN
    possible = get_possible_range(low, high, history, hints)
    if possible[0] > possible[1]:
        log_step(f"PLAN hints contradict each other {possible}, "
                 f"using the full range")
        possible = (low, high)
    log_step(f"PLAN numbers still possible: {possible[0]}-{possible[1]}")

    prompt = build_prompt(low, high, history, hints, possible, few_shot)

    for attempt in range(1, MAX_AI_TRIES + 1):
        # Step 2: ACT
        try:
            reply = ask_fn(prompt)
        except Exception as error:
            # only the start of the error, so the log stays readable
            short_error = str(error)[:120]
            log_step(f"ACT try {attempt}: AI call failed: {short_error}")
            continue
        log_step(f"ACT try {attempt}: AI replied {reply.strip()[:200]!r}")

        # Step 3: CHECK
        try:
            guess, reason = parse_reply(reply)
        except ValueError as error:
            log_step(f"CHECK try {attempt}: rejected, {error}")
            continue
        if not possible[0] <= guess <= possible[1]:
            log_step(f"CHECK try {attempt}: rejected, {guess} is outside "
                     f"{possible[0]}-{possible[1]}")
            continue

        log_step(f"CHECK try {attempt}: passed, guess={guess}")
        log_step("DONE source=ai")
        return {"guess": guess, "reason": reason, "source": "ai",
                "possible": possible, "trace": trace}

    # Fallback: the AI failed every try, so pick the middle ourselves.
    guess = (possible[0] + possible[1]) // 2
    reason = (f"The AI coach was unavailable, so this is the middle of "
              f"{possible[0]}-{possible[1]}.")
    log_step(f"FALLBACK guess={guess}")
    log_step("DONE source=fallback")
    return {"guess": guess, "reason": reason, "source": "fallback",
            "possible": possible, "trace": trace}


# ---------------------------------------------------------------------------
# Command line: run the coach without the game, for demos
# ---------------------------------------------------------------------------

USAGE = """Usage: python ai_coach.py LOW HIGH [GUESS:lower|higher ...]
Example: python ai_coach.py 1 100 45:lower 20:higher
(45:lower means you guessed 45 and the game said Go LOWER)"""


def _main(args):
    try:
        low, high = int(args[0]), int(args[1])
        history, hints = [], []
        for item in args[2:]:
            number, direction = item.split(":")
            if direction.lower() not in ("lower", "higher"):
                raise ValueError(direction)
            history.append(int(number))
            hints.append(f"Go {direction.upper()}!")
    except (IndexError, ValueError):
        print(USAGE)
        return

    advice = get_coach_advice(low, high, history, hints)
    for step in advice["trace"]:
        print(step)
    print()
    print(f"Coach suggests {advice['guess']} "
          f"(source: {advice['source']}): {advice['reason']}")


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
