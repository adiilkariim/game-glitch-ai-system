# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the hints were backwards").

### What did the game look like the first time I ran it, and what bugs did I notice?

The first time I ran the game, it looked like a normal number guessing game: a title, a sidebar to choose the difficulty, a box to type my guess, and buttons to submit or start a new game. But once I started playing, I noticed that many things did not work correctly. The "Go Higher" and "Go Lower" hints were backwards, so they pointed me in the wrong direction. The game also told me I was out of attempts while I still had one try left. On top of that, typing letters still used up an attempt, and after winning, clicking "New Game" did not actually let me play again.

**Bug Reproduction Log**

Document at least 3 bugs you found. Add rows as needed.

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
|-------|-------------------|-----------------|------------------------|
| Typed `kfadjgdfghf` and clicked "Submit Guess" | The game shows an error and does not count it as an attempt, because it is not a valid input | The game showed the error, but it still used up one of my attempts | On screen: "That is not a number." No console error |
| Typed `43095702347873234` and `-24356452054095` and clicked "Submit Guess" | The game shows an error message, because these numbers are outside the allowed range | The game accepted them as normal guesses and showed "Go HIGHER!" / "Go LOWER!" hints | On screen: "📈 Go HIGHER!" / "📉 Go LOWER!" No console error |
| Won a game, then clicked "New Game" and typed a new guess | The game fully restarts: history is cleared and I can play again | The attempts reset to 8 and the secret number changed, but the old history stayed and typing a guess did nothing | On screen: "You already won. Start a new game to play again." No console error |

### Where Each Bug Comes From in the Code

- **Invalid input uses up an attempt:** in `app.py`, `st.session_state.attempts += 1` runs as soon as "Submit Guess" is clicked, before `parse_guess` checks whether the input is valid. So even text like "kfadjgdfghf" counts as an attempt.
- **Out-of-range numbers are accepted:** in `logic_utils.py`, `parse_guess` only checks that the input can be turned into a number. It never checks the allowed range (like 1 to 100), so huge or negative numbers are treated as normal guesses.
- **The game can't restart after a win:** in `app.py`, winning sets `st.session_state.status = "won"`, but the "New Game" button only resets `attempts` and `secret`. It never sets `status` back to `"playing"` or clears `history`. Because the status is still `"won"`, the app hits `st.stop()` before it can read any new guess.

### Game Run Trace

Terminal output when I ran the game:

```
(.venv) PS ...\ai110-module1show-gameglitchinvestigator-starter> python -m streamlit run app.py
2026-10-03 15:06:34.834 Uvicorn server started on :::8501

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

#### A problem I faced while playing (proof the game was run)

When I typed letters ("kfadjgdfghf"), the game correctly showed "That is not a number." However, it still counted that as one of my attempts. Invalid input shouldn't cost an attempt.

---

## 🛠️ Bugs I Fixed

## Fixed Bug #1: Invalid input used up an attempt

**The bug:** typing letters like "kfadjgdfghf" showed "That is not a number." but still used up one of my attempts.

**Before** (`app.py`): the attempt was counted as soon as "Submit Guess" was clicked, before the input was checked.
```python
if submit:
    st.session_state.attempts += 1

    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.history.append(raw_guess)
        st.error(err)
    else:
        st.session_state.history.append(guess_int)
```

**After:** `attempts += 1` only runs after `parse_guess` confirms the input is valid.
```python
if submit:
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.error(err)
    ...
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)
```

Later, when I added the Guess History feature, invalid input also stopped being saved in the history, so the history only holds real guesses.

## Fixed Bug #2: One attempt was missing

**The bug:** Normal mode should allow 8 attempts but only allowed 7. Hard allowed 4 instead of 5, and Easy allowed 5 instead of 6.

**Before** (`app.py`): the counter started at `1`, so one attempt was already "used" before the first guess.
```python
if "attempts" not in st.session_state:
    st.session_state.attempts = 1
```

**After:** the counter starts at `0`, so each difficulty gets its full number of attempts.
```python
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
```

**Checked:** letters no longer cost an attempt, and each difficulty allows its full number of guesses.

## Fixed Bug #3: Fixing the inverted hints

**The bug:** the hints pointed the wrong way. A guess that was too high said "Go HIGHER!", and a guess that was too low said "Go LOWER!".

**Before** (`logic_utils.py`, `check_guess`):
```python
if guess > secret:
    return "Too High", "📈 Go HIGHER!"
else:
    return "Too Low", "📉 Go LOWER!"
```

**After:** the messages are swapped, so the hint points toward the secret.
```python
if guess > secret:
    return "Too High", "📉 Go LOWER!"
else:
    return "Too Low", "📈 Go HIGHER!"
```

**Second part of the bug:** even after swapping the messages, some hints were still wrong. On every even attempt, `app.py` turned the secret into text, so the guess and the secret were compared as text instead of numbers (for example, guess 100 vs secret 2 said "Go HIGHER!").

**Before** (`app.py`):
```python
if st.session_state.attempts % 2 == 0:
    secret = str(st.session_state.secret)
else:
    secret = st.session_state.secret

outcome, message = check_guess(guess_int, secret)
```

**After:** the secret is always passed as a number, so the hints are correct on every attempt.
```python
outcome, message = check_guess(guess_int, st.session_state.secret)
```

## Fixed Bug #4: Out-of-range numbers were accepted

**The bug:** numbers outside the difficulty's range (like `0`, `-43287543641542` or `352353`) were accepted as normal guesses and used up an attempt.

**Before** (`app.py`): every number went straight to `check_guess`, with no range check.
```python
else:
    st.session_state.attempts += 1
    st.session_state.history.append(guess_int)
    ...
    outcome, message = check_guess(guess_int, secret)
```

**After** (`app.py`): the guess is checked against the range first. Out-of-range numbers show an error and do not cost an attempt.
```python
elif guess_int < low or guess_int > high:
    st.session_state.history.append(guess_int)
    st.error(f"Out of range. Please enter a number between {low} and {high}.")
else:
    st.session_state.attempts += 1
    ...
```

## Fixed Bug #5: Decimals were cut down to whole numbers

**The bug:** typing `50.5` was quietly turned into `50` and counted as a guess.

**Before** (`logic_utils.py`, `parse_guess`):
```python
try:
    if "." in raw:
        value = int(float(raw))
    else:
        value = int(raw)
except Exception:
    return False, None, "That is not a number."
```

**After:** only whole numbers are accepted. Decimals get their own error message and do not cost an attempt.
```python
try:
    value = int(raw)
except Exception:
    try:
        float(raw)
    except Exception:
        return False, None, "That is not a number."
    return False, None, "Please enter a whole number."
```

## Fixed Bug #6: The secret could be outside the difficulty's range

**The bug:** the secret was picked only once, when the app opened in Normal mode (1 to 100). Switching to Hard (1 to 50) kept the old secret, so it could be a number like 81 that can't be guessed.

**Before** (`app.py`):
```python
if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)
```

**After:** changing the difficulty starts a new game with a secret inside the new range.
```python
if st.session_state.get("difficulty") != difficulty:
    st.session_state.difficulty = difficulty
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.status = "playing"
    st.session_state.history = []
```

## Fixed Bug #7: "Attempts left" updated one click late

**The bug:** the "Attempts left" box was drawn before the guess was processed, so it always showed the number from before my last guess. This made it look like invalid input was costing an attempt.

**Before** (`app.py`):
```python
st.info(
    f"Guess a number between 1 and 100. "
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)
```

**After:** the box is a placeholder that gets filled again after the guess is processed, so it always shows the correct number.
```python
attempts_box = st.empty()

def show_attempts_left():
    attempts_box.info(
        f"Guess a number between 1 and 100. "
        f"Attempts left: {attempt_limit - st.session_state.attempts}"
    )

show_attempts_left()
...
show_attempts_left()  # called again at the end, after the guess
```

**Checked:** in every mode, only whole numbers inside the range count as an attempt, the right error shows for everything else, and "Attempts left" updates right away.

## Fixed Bug #8: The game couldn't be restarted with "New Game"

**The bug:** after winning or losing, clicking "New Game" reset the attempts and changed the secret, but the old history stayed and typing a guess did nothing. The game stayed stuck until I refreshed the page. The new secret was also always picked from 1 to 100, so in Easy or Hard mode it could be a number I'm not allowed to enter.

**Before** (`app.py`): the button never reset `status` or `history`, and ignored the difficulty's range.
```python
if new_game:
    st.session_state.attempts = 0
    st.session_state.secret = random.randint(1, 100)
```

**After:** the button resets everything a new game needs. Because `status` is back to `"playing"`, the app no longer stops before reading the next guess.
```python
if new_game:
    st.session_state.attempts = 0
    st.session_state.secret = random.randint(low, high)
    st.session_state.status = "playing"
    st.session_state.history = []
```

**Checked:** after a win and after a loss, "New Game" starts a fresh game with empty history and full attempts, and new guesses get hints again. The new secret is always inside the selected mode's range.

---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion you did not accept as written (including what the AI suggested, why you rejected or changed it, and how you verified your version). It does not have to be a suggestion that was wrong: over-engineered, out of scope, harder to read, or a poor fit for this codebase all count.

### Which AI tools did I use on this project?

I mainly used Claude Code inside VS Code, running the Claude Opus 5 model. I also used a free AI model, GPT5-6 Luna, to help me organize my prompts and explain some things to me, so I would not run out of credits on Claude Code.

### An AI suggestion that was correct

I usually work with JavaScript, and while playing the game I noticed that the input box let me type numbers above 100, text, and negative numbers. My first idea was to fix this by blocking invalid keystrokes directly in the browser. What I forgot is that this would require JavaScript to control the input. The AI caught this and explained that adding JavaScript to a Streamlit app is possible, but it would be over-complicated for this assignment, so a simple error message in Python is the better fit. I agreed this was the correct approach.

### An AI explanation of a bug

I asked Claude to explain why the game could not be restarted after a win. After I won and clicked "New Game", the attempts reset and a new secret number appeared, but the old history stayed and typing a new guess did nothing. Claude explained that the "New Game" button resets the attempts and the secret number but forgets to set `status` back to `"playing"` and to clear `history`. Because the status is still `"won"`, the app shows "You already won. Start a new game to play again." and calls `st.stop()`, which stops the app before it can read any new guess. This also explained why refreshing the page fixed it: a refresh starts a new session where `status` starts as `"playing"` again.

### An AI suggestion I did not accept

When I organized my bug notes with Claude, it kept "the score goes negative" as a bug and asked what score I expected. I decided not to treat it as a bug, because losing points for wrong guesses makes sense in a guessing game. I verified this by checking `update_score`: a wrong guess subtracts 5 points, so a score of -5 after one wrong guess is expected.

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

### How did I decide whether a bug was really fixed?

I ran the app and played the game to see if the bug still happened, and I also checked the code to make sure the fix made sense. On top of that, I copied the code and gave it to multiple AI models to see if there was something that I or Claude Code had missed.

### A test I ran and what it showed me

The first time I ran `pytest`, all 3 tests failed with errors like `assert ('Win', '🎉 Correct!') == 'Win'`. This showed me that `check_guess` returns two values (the outcome and a message), while the tests only expected the outcome. After updating the tests to read only the outcome, they passed. I also added 4 new tests for bugs I fixed, like checking that a guess that is too high says "Go LOWER!" and that a decimal like `50.5` shows "Please enter a whole number." All 7 tests passed. I also tested manually: I played a full game in Normal mode, guessing 45, 20, 5 and 6, and the hints pointed the right way until I won.

### Did AI help me design or understand any tests?

Yes. When the tests failed, Claude explained that they were failing because `check_guess` returns two values instead of one, which helped me understand the error message. Claude also wrote the 4 new tests that target the bugs I fixed, and I ran `pytest` myself to confirm they all passed.

---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

### How I would explain reruns and session state to a friend

Every time you click on something, Streamlit runs the whole program again from the beginning, like the page is refreshing. Normal variables forget everything after each click, so you need to save important things like the secret number, the score, and the attempts in `st.session_state`, because it remembers them between clicks.

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

### A habit I want to reuse

The habit I want to build is carefully reading and understanding everything, even the parts I find hard. Staying focused and reading every detail is exhausting, and sometimes I catch myself writing vague prompts like "make it better." When I do that, the AI starts doing things I didn't want, because my prompt wasn't clear. So I need to build the habit of reading and evaluating what the AI gives me instead of just skipping over it.

### What I would do differently next time

Next time, I would write clearer and more specific prompts instead of vague ones like "make it better." When my prompt wasn't clear, the AI did things I didn't ask for, like writing extra answers I wanted to write myself. Telling the AI exactly what I want, and what I don't want it to change, would save me time and keep me in control of my own work.

### How this project changed the way I think about AI-generated code

AI can often write and generate code better and faster than I can, but only when I'm specific and clear, and when I evaluate everything it gives me. This project showed me that the parts I skip and accept without reading can cause more problems in the code later.
