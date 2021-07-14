__version__ = "0.0.1"

import warnings
with warnings.catch_warnings(): #ignore warnings
    warnings.simplefilter("ignore")
    
    import copy
    import os
    import matplotlib.pyplot as plt
    import numpy as np
    import gzip
    import numba
    from numba import njit
    import sidis
    import xarray as xr

    import PySpice.Logging.Logging as Logging
    from PySpice.Doc.ExampleTools import find_libraries
    from PySpice.Spice.Library import SpiceLibrary
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Unit import *
    
    import nptyping
    from nptyping import NDArray as Array
    from nptyping import get_type,Int,Float
    import typing
    from typing import (Optional, Tuple, Dict, Callable, 
                        Union, Mapping, Sequence, Iterable, 
                        Hashable, List, Any)
    
    from tqdm import tqdm
    
    from chaogate.core import *
    from chaogate.plotting import *