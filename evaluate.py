"""
Evaluation script for the AI Coach.

Runs the coach with the real Gemini model on 8 preset game situations,
once with the few-shot prompt and once with the baseline prompt (no
examples), and prints a pass/fail summary.

A case passes when all of these are true:
- the AI answered (no fallback was needed),
- the guess is the middle of the numbers still possible (within 1),
  which is the best strategy because each hint then removes half of them,
- the reply is clean JSON (no extra text or code block around it),
- the reason tells the player the exact numbers still possible
  (for example "21-44", "21 to 44" or "between 21 and 44").

Run it with:  python evaluate.py
"""

import time

from ai_coach import get_coach_advice

LOWER = "📉 Go LOWER!"
HIGHER = "📈 Go HIGHER!"

# (name, low, high, history, hints)
CASES = [
    ("Normal, first guess", 1, 100, [], []),
    ("Normal, 1 hint", 1, 100, [50], [LOWER]),
    ("Normal, 2 hints", 1, 100, [45, 20], [LOWER, HIGHER]),
    ("Easy, first guess", 1, 20, [], []),
    ("Easy, 2 hints", 1, 20, [10, 15], [HIGHER, LOWER]),
    ("Hard, 1 hint", 1, 50, [25], [HIGHER]),
    ("Normal, 4 hints", 1, 100, [50, 75, 62, 68],
     [HIGHER, LOWER, HIGHER, LOWER]),
    ("Normal, 1 number left", 1, 100, [50, 75, 62, 68, 65, 63],
     [HIGHER, LOWER, HIGHER, LOWER, LOWER, HIGHER]),
]

# Pause between AI calls so the free tier's per-minute limit is not hit
DELAY_SECONDS = 4


def run_case(case, few_shot):
    """Run one case and return a dict with the measurements."""
    name, low, high, history, hints = case
    advice = get_coach_advice(low, high, history, hints, few_shot=few_shot)
    possible_low, possible_high = advice["possible"]
    middle = (possible_low + possible_high) / 2

    answered = advice["source"] == "ai"
    first_try = any(step.startswith("CHECK try 1: passed")
                    for step in advice["trace"])
    picked_middle = abs(advice["guess"] - middle) <= 1

    # The last reply the AI sent, as written in the trace
    replies = [step for step in advice["trace"] if "AI replied '" in step]
    clean_json = bool(replies) and replies[-1].split("AI replied '")[1][0] == "{"

    reason = advice["reason"]
    if possible_low == possible_high:
        names_range = str(possible_low) in reason
    else:
        names_range = any(
            f"{possible_low}{sep}{possible_high}" in reason
            for sep in ("-", " to ", " and ")
        )

    return {
        "name": name,
        "possible": f"{possible_low}-{possible_high}",
        "guess": advice["guess"],
        "answered": answered,
        "first_try": first_try,
        "middle": picked_middle,
        "clean_json": clean_json,
        "names_range": names_range,
        "reason_words": len(reason.split()),
        "passed": answered and picked_middle and clean_json and names_range,
    }


def yes_no(value):
    return "yes" if value else "NO"


def print_results(mode, results):
    print(f"\n=== {mode} ===")
    print(f"{'Case':<24}{'Possible':<10}{'Guess':<7}{'AI':<5}"
          f"{'1st try':<9}{'Middle':<8}{'JSON':<6}{'Range':<7}"
          f"{'Words':<7}Result")
    for r in results:
        print(f"{r['name']:<24}{r['possible']:<10}{r['guess']:<7}"
              f"{yes_no(r['answered']):<5}{yes_no(r['first_try']):<9}"
              f"{yes_no(r['middle']):<8}{yes_no(r['clean_json']):<6}"
              f"{yes_no(r['names_range']):<7}{r['reason_words']:<7}"
              f"{'PASS' if r['passed'] else 'FAIL'}")


def summary_row(label, few, base, key):
    total = len(few)
    few_count = sum(r[key] for r in few)
    base_count = sum(r[key] for r in base)
    print(f"{label:<26}{few_count}/{total:<10}{base_count}/{total}")


def main():
    all_results = {}
    for few_shot in (True, False):
        mode = "Few-shot" if few_shot else "Baseline"
        results = []
        for case in CASES:
            results.append(run_case(case, few_shot))
            time.sleep(DELAY_SECONDS)
        print_results(mode, results)
        all_results[mode] = results

    few, base = all_results["Few-shot"], all_results["Baseline"]
    print("\n=== SUMMARY ===")
    print(f"{'':<26}{'Few-shot':<12}Baseline")
    summary_row("AI answered", few, base, "answered")
    summary_row("Valid on 1st try", few, base, "first_try")
    summary_row("Picked the middle", few, base, "middle")
    summary_row("Clean JSON reply", few, base, "clean_json")
    summary_row("Reason names the range", few, base, "names_range")
    summary_row("Overall PASS", few, base, "passed")
    few_words = sum(r["reason_words"] for r in few) / len(few)
    base_words = sum(r["reason_words"] for r in base) / len(base)
    print(f"{'Avg reason length':<26}{few_words:<12.1f}{base_words:.1f}"
          f"  (words)")


if __name__ == "__main__":
    main()
