def sort_tuple(t: tuple[str, str]) -> tuple[str, str]:
    return (t[0], t[1]) if t[0] < t[1] else (t[1], t[0])
