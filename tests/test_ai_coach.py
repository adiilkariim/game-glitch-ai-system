import inspect

from ai_coach import get_coach_advice, get_possible_range, parse_reply

LOWER = "📉 Go LOWER! 🧊 Cold"
HIGHER = "📈 Go HIGHER! 🌡️ Warm"


def mock_ai(*replies):
    """
    Make a mock AI (a stand-in for Gemini) that returns the given replies
    in order, so the tests run without internet or an API key. A reply
    that is an Exception is raised instead, like a failed API call. The
    prompts it receives are saved in mock.prompts.
    """
    replies = list(replies)

    def mock(prompt):
        mock.prompts.append(prompt)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    mock.prompts = []
    return mock


def test_possible_range_uses_the_hints():
    # 45 -> Go LOWER and 20 -> Go HIGHER leaves only 21 to 44
    assert get_possible_range(1, 100, [45, 20], [LOWER, HIGHER]) == (21, 44)


def test_parse_reply_reads_json_inside_extra_text():
    # The AI sometimes wraps the JSON in a code block
    text = '```json\n{"guess": 32, "reason": "middle of 21-44"}\n```'
    assert parse_reply(text) == (32, "middle of 21-44")


def test_good_ai_answer_is_accepted():
    ai = mock_ai('{"guess": 32, "reason": "middle of 21-44"}')
    advice = get_coach_advice(1, 100, [45, 20], [LOWER, HIGHER], ask_fn=ai)
    assert advice["source"] == "ai"
    assert advice["guess"] == 32
    assert len(ai.prompts) == 1


def test_broken_answer_is_retried():
    # Guardrail: the first reply is not JSON, so the coach asks again
    ai = mock_ai("I think 32!", '{"guess": 32, "reason": "middle"}')
    advice = get_coach_advice(1, 100, [45, 20], [LOWER, HIGHER], ask_fn=ai)
    assert advice["source"] == "ai"
    assert advice["guess"] == 32
    assert len(ai.prompts) == 2


def test_out_of_range_guess_is_rejected():
    # Guardrail: 90 is impossible after 45 -> Go LOWER, so it is rejected
    ai = mock_ai('{"guess": 90, "reason": "x"}',
                 '{"guess": 32, "reason": "middle"}')
    advice = get_coach_advice(1, 100, [45, 20], [LOWER, HIGHER], ask_fn=ai)
    assert advice["guess"] == 32
    assert any("outside 21-44" in step for step in advice["trace"])


def test_ai_failure_falls_back_to_the_middle():
    # Guardrail: if the AI fails every try, the game still gets a guess
    ai = mock_ai(RuntimeError("503 UNAVAILABLE"),
                 RuntimeError("503 UNAVAILABLE"))
    advice = get_coach_advice(1, 100, [45, 20], [LOWER, HIGHER], ask_fn=ai)
    assert advice["source"] == "fallback"
    assert advice["guess"] == 32


def test_secret_is_never_sent_to_the_ai():
    # Guardrail: the coach has no way to receive the secret, and the
    # prompt only holds what the player can already see
    assert "secret" not in inspect.signature(get_coach_advice).parameters
    secret = 37
    ai = mock_ai('{"guess": 32, "reason": "middle"}')
    get_coach_advice(1, 100, [45, 20], [LOWER, HIGHER], ask_fn=ai)
    assert str(secret) not in ai.prompts[0]


def test_every_step_is_logged():
    ai = mock_ai('{"guess": 32, "reason": "middle"}')
    advice = get_coach_advice(1, 100, [45, 20], [LOWER, HIGHER], ask_fn=ai)
    steps = [step.split()[0] for step in advice["trace"]]
    assert steps == ["START", "PLAN", "ACT", "CHECK", "DONE"]
