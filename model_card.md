# Model Card: AI Coach

## Overview

| | |
|---|---|
| **System** | AI Coach inside the Game Glitch Investigator number-guessing game |
| **Type** | Agentic workflow: PLAN → ACT → CHECK → LOG, with a specialized few-shot prompt |
| **Model** | Google Gemini `gemini-3.5-flash-lite` (free tier), temperature 0 |
| **Code** | `ai_coach.py`, used by the 🤖 button in `app.py` |
| **Input** | The difficulty's range, the player's valid guesses and their Higher/Lower hints. Never the secret number. |
| **Output** | A suggested next guess and a one-sentence reason, or a fallback suggestion if the AI fails |
| **Intended use** | Helping a player of this game decide their next guess and learn the "guess the middle" strategy. The player decides whether to follow it. |

## Limitations and Biases

- **The game is simple, so the coach has little to reason about.** With
  Higher/Lower hints, the best move is always the middle of the numbers still
  possible. Plain code can do this too; the AI mainly adds the explanation.
- **It depends on an external service.** If Gemini is down, overloaded
  (`503`), out of free quota, or the key is wrong, the coach can only give
  the fallback suggestion, which has no AI explanation. During development,
  one model was retired (`404`) and larger models were often overloaded.
- **The AI is not fully consistent.** Even at temperature 0, the wording of
  the reason changes between runs. The suggested number stayed the same in
  our checks, but this is not guaranteed.
- **The AI's reason is not checked.** The CHECK step verifies the guess and
  the format, but not whether the sentence is true. A reason could name the
  wrong range while the guess is still valid.
- **Rounding bias.** When there is an even count of numbers left (for example
  13-14), there are two "middles". The fallback always picks the lower one,
  and Gemini usually does too, so the coach leans toward lower numbers.
- **English only,** and the evaluation covers only 8 situations.
- **Latency:** each answer takes a few seconds.

## Misuse and Prevention

| Possible misuse | How it is prevented or limited |
|---|---|
| Using the AI to find out the secret | The agent has no way to receive the secret (`get_coach_advice` has no `secret` parameter), and a test checks that the secret is never in the prompt. |
| Prompt injection (typing text to control the AI) | Nothing the player types reaches the prompt as text. Guesses must pass `parse_guess` and the range check, so only whole numbers and the game's own hints are used. |
| Leaking the API key | The key lives in `.env`, which is in `.gitignore`. It is never logged or shown. |
| Using up the free quota by clicking many times | Each click makes at most 2 AI calls. If the quota runs out, the fallback keeps the game working. |
| Making the game too easy | The coach is optional and only suggests; the player still types each guess. A future version could subtract points for using it. |
| Trusting a wrong AI answer | The CHECK step rejects impossible guesses, and the fallback is clearly labeled "Fallback suggestion". |

## Testing Results

- **Unit tests:** 17 out of 17 pass: 9 for the game logic and 8 for the AI
  Coach guardrails (retry, rejecting bad answers, fallback, no secret,
  logging). The coach tests use a mocked AI, so they can force failures.
- **Evaluation:** `evaluate.py` runs the real Gemini on 8 game situations with
  the specialized prompt and with a plain baseline prompt (only the range and
  the guesses: no strategy, no examples, no possible range).

| Measure | Specialized prompt | Baseline prompt |
|---|---|---|
| AI answered | 8/8 | 8/8 |
| Picked the middle | 8/8 | 8/8 |
| Clean JSON reply | 8/8 | 4/8 |
| Reason names the numbers still possible | 8/8 | 3/8 |
| **Overall pass** | **8/8** | **1/8** |
| Average reason length | 11.0 words | 14.2 words |

Example for the same situation (45 → Go LOWER, 20 → Go HIGHER):
- Specialized: *"32 is the middle of the remaining numbers from 21 to 44."*
- Baseline: *"Since the number is between 20 and 45, 32 is the midpoint for the next guess."*

Note: the first version of the evaluation only measured whether the guess was
right and found no difference. The two format and explanation measures were
added after that run, and the baseline was changed to a truly plain prompt.

## What Surprised Me While Testing

What surprised me most was that the AI didn't need the few-shot examples to
pick the right number. Without the examples and the strategy, Gemini still
chose the best guess (the middle of the numbers still possible) in 8 out of 8
cases. The examples didn't make it smarter at the game; they changed how it
answered. With the specialized prompt it always replied in clean JSON and
told the player exactly which numbers were left, while the plain prompt often
gave vague reasons like "statistically optimal" and sometimes broke the reply
format. This showed me that a prompt can control the style and reliability of
an AI's answer even when the model already knows how to solve the problem.

## AI Collaboration

### How I used AI

I used AI in two ways. First, as an explainer: it helped me understand the
project, the assignment and things I didn't know yet. Second, as a tool to
build my ideas. I had the main idea, and the AI helped me turn it into code,
designs and documentation. Every time it gave me an idea, code or a design
suggestion, I evaluated it and tested it, keeping what worked and changing
what didn't, until I got the result I wanted.

### A suggestion I accepted

I accepted the AI's suggestion to build the AI Coach as an agent with 4
steps: plan, act, check and log. I accepted it because it made the AI part
easy to understand and easy to check. The planning step is plain Python, so
the AI only has a small job, and the check step catches its mistakes before
the player sees them. It also covered most of what the assignment asked for,
such as guardrails, logging and testing, with one feature.

### Suggestions I rejected or changed

I changed several of the AI's design suggestions to fit what I wanted. The AI
first put the AI Coach button in a row with the other buttons and showed its
answer in a blue info box. I didn't like that, so I asked for a square button
with the 🤖 emoji in the bottom-right corner, with the answer shown in a box
of the same style right next to it, and the "AI Coach is thinking..." message
in the same spot. I also asked the AI to shorten the architecture diagram,
because its first versions were too long and hard to follow. I also changed
how the tests were described: the AI called the replacement for Gemini in the
unit tests a "fake AI", and I asked it to rename it to "mock AI", because
"fake" made the tests sound less real even though they are real tests. I made
these changes because they made the game feel better to play and made the
project clearer and more professional for someone reading it.

## Future Improvements

Right now the game is simple: only three small ranges and Higher/Lower hints,
so the best strategy is always to guess the middle, and the AI Coach doesn't
have much to think about. If I had more time, I would improve the game
itself, for example with bigger ranges, new hint types or new rules. A richer
game would also make the AI Coach more useful, because it would have to
reason about more than just picking the middle number.
