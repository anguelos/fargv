import inspect


def get_outermost_invoker_docstring(frame=None):
    if frame is None:
        frame = inspect.currentframe()

    if frame.f_back is None:
        # Reached the top-level script/module
        docstring = frame.f_globals['__doc__']
        if docstring is None:
            return ''
        return docstring
    
    # Recursively traverse the call stack
    return get_outermost_invoker_docstring(frame.f_back)