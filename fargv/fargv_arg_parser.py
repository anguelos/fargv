from .fargv_param_registry import FargvName, FargvRegistry, FargvNameException, FargvDuplicateNameException, __registry as __registry
from .fargv_param_definition import FargvBool, FargvInt, FargvFloat, FargvStr, FargvRefStr, FargvFname, FargvExistingFname, FargvMissingFname, FargvParamException


def define_by_list(args_list):
    pass
    # for arg in args_list:
    #     if isinstance(arg, str):
    #         pass
    #     elif isinstance(arg, dict):
    #         pass
    #     elif isinstance(arg, tuple):
    #         pass
    #     else:
    #         raise ValueError("Invalid argument type")
    #     # if isinstance(arg, str):
    #     #     pass
    #     # elif isinstance(arg, dict):
    #     #     pass
    #     #
    

def define_by_dict(args_dict):
    pass