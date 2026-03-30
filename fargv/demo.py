"""Demo functions for ``python -m fargv fargv.demo.<function>``.

These functions are designed to showcase how :func:`fargv.parse` infers a
typed CLI from a plain Python signature.  Every parameter has an explicit
Python type so the help output and type coercion are accurate.

Examples
--------
::

    python -m fargv fargv.demo                          # list available demos
    python -m fargv fargv.demo.fibonacci --n=20
    python -m fargv fargv.demo.collatz --n=27
    python -m fargv fargv.demo.text_stats --text="hello world"
    python -m fargv fargv.demo.bmi --weight_kg=70.0 --height_m=1.75
"""


def fibonacci(n: int = 10, zero_indexed: bool = True) -> str:
    """Return the first *n* Fibonacci numbers as a space-separated string.

    :param n:            How many Fibonacci numbers to generate.
    :param zero_indexed: When True the sequence starts F(0)=0; when False F(1)=1.
    """
    a, b = (0, 1) if zero_indexed else (1, 1)
    result = []
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return " ".join(str(x) for x in result)


def collatz(n: int = 27) -> str:
    """Return the Collatz sequence starting from *n* as a space-separated string.

    The sequence terminates at 1 following the rule:
    n → n/2 (even) or 3n+1 (odd).

    :param n: Starting integer (must be ≥ 1).
    """
    if n < 1:
        return "n must be >= 1"
    seq = [n]
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        seq.append(n)
    return " ".join(str(x) for x in seq)


def text_stats(text: str = "the quick brown fox jumps over the lazy dog",
               lower: bool = True) -> str:
    """Return basic statistics about *text*.

    :param text:  Input string to analyse.
    :param lower: Normalise to lower-case before counting.
    """
    if lower:
        text = text.lower()
    words  = text.split()
    chars  = len(text.replace(" ", ""))
    unique = len(set(words))
    return (
        f"chars={chars}  words={len(words)}  unique_words={unique}  "
        f"avg_word_len={chars/len(words):.2f}"
    )


def bmi(weight_kg: float = 70.0, height_m: float = 1.75,
        verbose: bool = False) -> str:
    """Compute Body Mass Index (BMI = weight / height²).

    :param weight_kg: Body weight in kilograms.
    :param height_m:  Height in metres.
    :param verbose:   When True include the WHO category label.
    """
    bmi_val = weight_kg / height_m ** 2
    msg = f"BMI={bmi_val:.2f}"
    if verbose:
        if   bmi_val < 18.5: category = "Underweight"
        elif bmi_val < 25.0: category = "Normal weight"
        elif bmi_val < 30.0: category = "Overweight"
        else:                category = "Obese"
        msg += f"  ({category})"
    return msg
