import sys
from datetime import datetime
import inspect


class FargvParamException(Exception):
    pass


class FargvNameException(Exception):
    pass


verbosity = 1

def set_verbosity(v):
    global verbosity
    verbosity = v

def get_verbosity():
    global verbosity
    return verbosity

def warn(msg, verbose=1, file=sys.stderr, end="\n", put_timestamp=False):
    if verbosity >= verbose:
        if put_timestamp:
            now = datetime.now()
            timestamp = f"{now.strftime('%Y/%m/%d:%H:%M:%S')}# "
        else:
            timestamp = ""
        print(f"{timestamp}{msg}", file=file, end=end)
