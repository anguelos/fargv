#from .argv_parser import fargv, fargv2dict, t_fargv_args
#from .util import get_verbosity, set_verbosity, warn
import sys

from .fargv_param_registry import Name, Registry, FargvNameException, FargvDuplicateNameException
#from .fargv_param_definition import FargvBool, FargvInt, FargvFloat, FargvStr, FargvRefStr, FargvFname, FargvExistingFname, FargvMissingFname, FargvParamException
from .fargv_param_value import ParamDefinition, Bool, Int, Float, Str, StrRef, Choice, Literal, Src, Sequence, FargvValueNotAllowedError, type_from_definition_data, create_from_definition_data

from .fargv_argparser import FargvArgparseException, UnixArgParser
from .fargv_legacy import fargv as fargv_legacy

def fargv(*args):
    sys.stderr.write(f"Warning: fargv is deprecated and will be removed in the future. Use fargv_legacy instead.\n")
    return fargv_legacy(*args)


all = [
    "fargv", "fargv_legacy", "FargvBool", "FargvInt", "FargvFloat", "FargvStr", "FargvFilename", "FargvExistingFname", "FargvMissingFname", "FargvParamException", "__registry",
]
