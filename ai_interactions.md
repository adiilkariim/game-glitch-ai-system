# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Final Project: AI Coach Agent Traces

The AI Coach (`ai_coach.py`) is a multi-step agent: **PLAN** (work out the
numbers still possible), **ACT** (ask Gemini), **CHECK** (validate the reply,
retry once, fall back if needed) and **LOG**. Every step is written to
`logs/coach.log`. Below are real traces copied from that log (the log folder
itself is not committed). Long error messages are shortened with `...`.

### Trace 1: Normal run, the AI's answer passes the check

Normal mode, after 45 → Go LOWER and 20 → Go HIGHER.
```
2026-11-07 00:54:55,606 INFO START range=1-100 history=[45, 20] mode=few-shot
2026-11-07 00:54:55,607 INFO PLAN numbers still possible: 21-44
2026-11-07 00:55:00,153 INFO ACT try 1: AI replied '{"guess": 32, "reason": "32 is the middle of the remaining numbers 21 to 44."}'
2026-11-07 00:55:00,153 INFO CHECK try 1: passed, guess=32
2026-11-07 00:55:00,154 INFO DONE source=ai
```
**Reasoning:** the PLAN step narrowed 1-100 down to 21-44 from the two hints,
Gemini picked the middle (32), and the CHECK step confirmed 32 is inside
21-44 before the player saw it.

### Trace 2: Retry, Gemini was overloaded on the first try

During `evaluate.py` (baseline prompt), with only one number left.
```
2026-11-06 23:59:23,359 INFO START range=1-100 history=[50, 75, 62, 68, 65, 63] mode=baseline
2026-11-06 23:59:23,359 INFO PLAN numbers still possible: 64-64
2026-11-06 23:59:24,373 INFO ACT try 1: AI call failed: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. ...
2026-11-06 23:59:27,941 INFO ACT try 2: AI replied '{"guess": 64, "reason": "64 is the only remaining possible number."}'
2026-11-06 23:59:27,941 INFO CHECK try 2: passed, guess=64
2026-11-06 23:59:27,941 INFO DONE source=ai
```
**Reasoning:** the first call failed, so the agent decided to try again
instead of giving up. The second answer (64) passed the check.

### Trace 3: Fallback, the AI failed on both tries

While testing the larger `gemini-3.8-flash` model, which was overloaded.
```
2026-11-06 23:21:04,295 INFO START range=1-100 history=[45, 20] mode=baseline
2026-11-06 23:21:04,295 INFO PLAN numbers still possible: 21-44
2026-11-06 23:21:07,281 INFO ACT try 1: AI call failed: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. ...
2026-11-06 23:21:10,151 INFO ACT try 2: AI call failed: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. ...
2026-11-06 23:21:10,151 INFO FALLBACK guess=32
2026-11-06 23:21:10,151 INFO DONE source=fallback
```
**Reasoning:** after 2 failed tries the agent stopped calling the AI and used
the result of its own PLAN step (the middle of 21-44), so the game kept
working. This failure is why the game now uses `gemini-3.5-flash-lite`.

---

## Module 1: Agent Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked Claude to add a Guess History to the sidebar that shows only valid guesses, and then to show the hint next to each guess.

**What did the agent do?**

- Edited `app.py` only.
- Stopped saving invalid and out-of-range input in the history.
- Added a "Guess History" section to the sidebar that updates after every guess.
- Saved each guess's hint in a new `hints` list and showed it next to the guess (for example, `45 → Go LOWER! Cold`).
- Cleared the history and hints on New Game and when the difficulty changes.
- Tested it and checked that all pytest tests still pass.

**What did you have to verify or fix manually?**

I tested it myself in the browser to make sure it only shows valid guesses. I decided that hints should be hidden in the sidebar when "Show hint" is off, and I chose to keep the History line in the Developer Debug Info panel.

### Second example: moving the game logic into logic_utils.py

**My prompt to move the game logic from app.py to logic_utils.py:**
```
I want to move the logic code from app.py to logic_utils.py, and I want to start with get_range_for_difficulty. Move it from app.py to logic_utils.py, but keep the UI code in the app.py file.
```

**What did the agent do?**

- Moved `get_range_for_difficulty` into `logic_utils.py`, replacing the placeholder that raised an error.
- Deleted the old copy from `app.py` and added the import `from logic_utils import get_range_for_difficulty`.
- Checked that the function returned the same ranges as before and that `app.py` still worked.
- Pointed out that Hard mode (1 to 50) is easier than Normal (1 to 100), which could be fixed later.

**What did you have to verify or fix manually?**

I checked that all the UI code stayed in `app.py` and only the logic was moved. After this first function worked, I asked the AI to move the other functions (`parse_guess`, `check_guess` and `update_score`) the same way. I decided to keep the Hard mode range as it was.

---

## Test Generation (SF7)

> Document how you used AI to help generate or improve tests.

| Edge Case | Prompt Used | AI-Suggested Test | Did It Pass? | Your Reasoning |
|-----------|-------------|-------------------|--------------|----------------|
| Non-numeric string | Write a pytest test for parse_guess in logic_utils.py that checks letters like "fghalkhfsga" are rejected. The test should check that ok is False and the error message is "That is not a number." | `test_letters_are_rejected` | ✅ Yes | Players can type anything in the box, so letters must show an error instead of being treated as a guess. |
| Decimal number | Write a pytest test for parse_guess that checks a decimal like "50.5" is rejected, because only whole numbers should be accepted. The test should check that ok is False and the error message is "Please enter a whole number." | `test_decimal_is_rejected` | ✅ Yes | Decimals used to be quietly cut down (50.5 became 50), so I wanted to make sure only whole numbers are accepted now. |
| Empty input | Write a pytest test for parse_guess that checks an empty input "" is rejected, so clicking Submit Guess with an empty box doesn't count as a guess. The test should check that ok is False and the error message is "Enter a guess." | `test_empty_input_is_rejected` | ✅ Yes | It's easy to click Submit by accident with an empty box, and that shouldn't cost an attempt. |
| Symbols only | Write a pytest test for parse_guess that checks an input with only symbols like "@#$" is rejected. The test should check that ok is False and the error message is "That is not a number." | `test_symbols_are_rejected` | ✅ Yes | I thought symbols were costing me attempts while playing, so I wanted a test proving they are rejected. |

---

## Linting & Style (SF9)

> Document your use of AI for linting or code style improvements.

**Prompt used:**

```
I asked Claude to fix the flake8 style warnings and improve the docstrings in logic_utils.py, without changing any game logic, player messages, function names, or the CSS animation, and to show me the plan before making changes.
```

**Linting output before:**

```
57 warnings from flake8 across app.py, logic_utils.py and tests/test_game_logic.py:
E265 block comment should start with '# '  (18)
E501 line too long (> 79 characters)        (27)
E302 expected 2 blank lines                 (12)
E305 expected 2 blank lines after function  (2)
```

**Changes applied:**

- Added a space after `#` in all comments (E265).
- Split long comments over multiple lines without changing the words, and wrapped a few long code lines (E501).
- Added the missing blank lines around functions (E302, E305).
- Rewrote the docstrings of all 5 functions in `logic_utils.py` to describe their inputs and return values.
- After the changes, flake8 shows 0 warnings and all 9 pytest tests still pass.

---

## Model Comparison (SF11)

> Compare two AI models on the same task.

**Task:** I gave Claude and GPT5-6 Luna the same buggy `check_guess` code and asked them to find and fix all the bugs causing wrong hints.

**Results:** Both found the reversed hint messages and the bug where the secret becomes text on even attempts. Claude's fix was more Pythonic: it kept the secret as a number and removed the unnecessary `try/except`. Luna added extra input validation.

**Clearer explanation:** Claude, because it used the example `"9" > "50"` to show why the hints looked random.

**Preferred:** Claude, for the clearer explanation and simpler fix. Luna was still useful for handling invalid input.
