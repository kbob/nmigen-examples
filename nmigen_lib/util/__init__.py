from .main import main, Main

__all__ = ['delay', 'main', 'Main']

def delay(n):
    """delay n clocks
    Use in an async process:

        yield from delay(n)
    """
    return [None] * n
