import random
import streamlit as st
# FIX: I asked Claude to move the game logic out of app.py; it moved the 4
# functions into logic_utils.py and updated this import, keeping only the UI
# here
from logic_utils import (
    get_range_for_difficulty,
    parse_guess,
    check_guess,
    update_score,
    get_temperature,
)
# AI FEATURE: the AI Coach agent that suggests the next guess
from ai_coach import get_coach_advice

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

# UI: the game controller emoji in the title plays a looping wiggle animation
st.markdown(
    """
    <style>
    @keyframes controller-wiggle {
        0%, 100% { transform: rotate(0deg) translateY(0); }
        25% { transform: rotate(-12deg) translateY(-4px); }
        50% { transform: rotate(0deg) translateY(0); }
        75% { transform: rotate(12deg) translateY(-4px); }
    }
    .game-icon {
        display: inline-block;
        animation: controller-wiggle 1.5s ease-in-out infinite;
    }
    </style>
    <h1><span class="game-icon">🎮</span> Game Glitch Investigator</h1>
    """,
    unsafe_allow_html=True,
)
st.caption("An AI-generated guessing game. Something is off.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

attempt_limit_map = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 5,
}
attempt_limit = attempt_limit_map[difficulty]

low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)

# FIX: I noticed Normal mode only gave 7 attempts instead of 8; Claude found
# the counter started at 1, changed it to 0, and tested every difficulty
if "attempts" not in st.session_state:
    st.session_state.attempts = 0

if "score" not in st.session_state:
    st.session_state.score = 0

if "status" not in st.session_state:
    st.session_state.status = "playing"

if "history" not in st.session_state:
    st.session_state.history = []

# FEATURE: the hint of each guess is saved too, so the sidebar can show it
# next to the guess
if "hints" not in st.session_state:
    st.session_state.hints = []

# FIX: I asked Claude to fix it after it found Hard mode could keep a secret
# like 81 that can't be guessed; now changing the difficulty starts a new game
# with a secret in range
if st.session_state.get("difficulty") != difficulty:
    st.session_state.difficulty = difficulty
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.hints = []

st.subheader("Make a guess")

# FIX: I thought symbols were costing an attempt; Claude found "Attempts left"
# updated one click late and made this box refresh after each guess
attempts_box = st.empty()


def show_attempts_left():
    attempts_box.info(
        f"Guess a number between {low} and {high}. "
        f"Attempts left: {attempt_limit - st.session_state.attempts}"
    )


show_attempts_left()

# FEATURE: the sidebar shows the guesses of the current game, filled again
# after each guess so it is always up to date
history_box = st.sidebar.empty()


def show_guess_history():
    # the hint is only shown when "Show hint" is on, so the sidebar doesn't
    # reveal hidden hints
    hints_visible = st.session_state.get("show_hint", True)
    with history_box.container():
        st.markdown("### 📜 Guess History")
        if st.session_state.history:
            for number, guess in enumerate(st.session_state.history, start=1):
                has_hint = number <= len(st.session_state.hints)
                if hints_visible and has_hint:
                    hint = st.session_state.hints[number - 1]
                    st.write(f"{number}. {guess} → {hint}")
                else:
                    st.write(f"{number}. {guess}")
        else:
            st.caption("No guesses yet.")


show_guess_history()

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}"
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    ask_coach = st.button("Ask AI Coach 🤖")
with col4:
    show_hint = st.checkbox("Show hint", value=True, key="show_hint")

# FIX: I found the game got stuck after a win; Claude found New Game never
# reset the status or history and always used 1-100, fixed all three, and
# tested it after a win and a loss
if new_game:
    st.session_state.attempts = 0
    st.session_state.secret = random.randint(low, high)
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.hints = []
    st.success("New game started.")
    st.rerun()

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success("You already won. Start a new game to play again.")
    else:
        st.error("Game over. Start a new game to try again.")
    st.stop()

# AI FEATURE: the coach only gets the range, the guesses and their hints,
# never the secret. Asking it does not cost an attempt, and the player
# decides whether to follow its suggestion.
if ask_coach:
    with st.spinner("The AI Coach is thinking..."):
        advice = get_coach_advice(
            low, high, st.session_state.history, st.session_state.hints
        )
    if advice["source"] == "ai":
        st.info(
            f"🤖 Coach suggests **{advice['guess']}**: {advice['reason']}"
        )
    else:
        st.warning(
            f"🤖 Fallback suggestion **{advice['guess']}**: "
            f"{advice['reason']}"
        )

if submit:
    ok, guess_int, err = parse_guess(raw_guess)

    # FEATURE: invalid and out-of-range input is no longer saved in the
    # history, so it only holds real guesses
    if not ok:
        st.error(err)
    # FIX: I found huge and negative numbers were accepted and asked for an
    # error that doesn't cost an attempt; Claude added this range check and
    # tested it in every mode
    elif guess_int < low or guess_int > high:
        st.error(
            f"Out of range. Please enter a number between {low} and {high}."
        )
    else:
        # FIX: I found while playing that letters still used up an attempt;
        # Claude moved attempts += 1 after the input check, and I tested it
        # in the game
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)

        # FIX: I asked Claude to finish the hint fix after it found the secret
        # was turned into text on even attempts; now the secret is always
        # compared as a number
        outcome, message = check_guess(guess_int, st.session_state.secret)

        # UI: wrong guesses also show a Hot/Warm/Cold emoji next to the hint
        if outcome != "Win":
            temperature = get_temperature(
                guess_int, st.session_state.secret, low, high
            )
            message = f"{message} {temperature}"

        st.session_state.hints.append(message)

        if show_hint:
            st.warning(message)

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"You won! The secret was {st.session_state.secret}. "
                f"Final score: {st.session_state.score}"
            )
        else:
            if st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"Out of attempts! "
                    f"The secret was {st.session_state.secret}. "
                    f"Score: {st.session_state.score}"
                )

show_attempts_left()
show_guess_history()

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
