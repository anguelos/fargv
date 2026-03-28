import sys





from .fargv_legacy import fargv as fargv_legacy

def fargv(*args):
    sys.stderr.write(f"Warning: fargv is deprecated and will be removed in the future. Use fargv_legacy instead.\n")
    return fargv_legacy(*args)


all = [
    "fargv", "fargv_legacy",
]
