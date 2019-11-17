

def delay(n):
    """delay n clocks
    Use in an async process:

        yield from delay(n)
    """
    return [None] * n
