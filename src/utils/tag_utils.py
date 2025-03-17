import typing
from difflib import SequenceMatcher


def get_similarity(a: str, b: str) -> float:
    # returns a value between 0 and 1, where 1 means exact
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fuzzy_search(
    query: str, choices: dict[str, typing.Any], threshold: float = 0.6
) -> list[tuple[str, float]]:
    if not query or not choices:
        return []

    # calculate similarity for each choice
    results = [(name, get_similarity(query, name)) for name in choices.keys()]

    # filter by threshold and sort by score (descending)
    results = [r for r in results if r[1] >= threshold]
    results.sort(key=lambda x: x[1], reverse=True)

    return results
