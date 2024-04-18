#from .argv_parser import fargv, fargv2dict, t_fargv_args
#from .util import get_verbosity, set_verbosity, warn

from .fargv_param_registry import FargvName, FargvRegistry, FargvNameException, FargvDuplicateNameException, __registry as __registry
from .fargv_param_definition import FargvBool, FargvInt, FargvFloat, FargvStr, FargvRefStr, FargvFname, FargvExistingFname, FargvMissingFname, FargvParamException


def clear_registry():
    __registry.clear()


all = [
    "FargvBool","FargvInt","FargvFloat","FargvStr","FargvFilename","FargvExistingFname","FargvMissingFname","FargvParamException", "__registry",
]
