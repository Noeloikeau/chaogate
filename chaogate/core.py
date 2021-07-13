# AUTOGENERATED! DO NOT EDIT! File to edit: 00_functions.ipynb (unless otherwise specified).

__all__ = ['global_path', 'chaogate', 'tup2ar', 'sweep', 'iterate_map', 'iterate', 'lyapunov', 'grid', 'bifurcate',
           'booleanize_ar', 'booleanize', 'boolean_gradient', 'boolean_divergence']

# Cell
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

# Cell
global_path = r'C:\Anaconda3\Lib\site-packages\PySpice\Examples\libraries\chaogate'

# Cell
def chaogate(path : str = global_path,
             Vdd : float = 1.2,
             Vin : Optional[float] = 0.45,
             Vbias : float = 0.45,
             w1 = 120e-9,
             w2 = 120e-9,
             w3 = 2000e-9,
             l1 = 65e-9,
             l2 = 65e-9,
             l3 = 65e-9,
             capacitance : int = 1e-15,
             noise : Optional[float] = 0,
             noise_type : str = 'gaussian',
             noise_duration : int = 1e-9,
             noise_delay : int = 0,
             time_delay : int = 1e-9,
             impedance : int = 50,
             TEMP = None
            ):
    '''
    Constructs PySpice circuit object for a chaogate.

    Parameters:

        `path` : location of folder containing following spice files
               '65nm_bulk.lib','bsim4.out','bsim4v5.out','nmos.mod','pmos.mod'

        `vdd` : static positive terminal voltage in Volts.
            If `noise` is not 0 or None, a random source of `noise_type`
            fluctuating about `vdd` with amplitude `noise` is used to
            represent the supply voltage, with fluctuation lasting
            `noise_duration` ever `noise_delay` seconds.

        `vin` : static input voltage in Volts.
            If vin=0 or None, it is replaced with a transmission line having
            the `time_delay` and `impedance` args that connects `vin` to `vout`.

        `vbias` : bias voltage in Volts. This changes the MOSFET behavior.

        `widths` : MOSFET widths of the three transistors in Meters

        `lengths` : MOSFET lengths of the three transistors in Meters

        `capacitance` : capacitor constant in Farads
    '''

    #setup circuit, library, logger
    circuit=Circuit('Three MOSFET Chaogate')
    circuit.logger = Logging.setup_logging()
    circuit.spice_library = SpiceLibrary(path)
    circuit.include(circuit.spice_library['nmos'])
    circuit.include(circuit.spice_library['pmos'])

    #give unchanging circuit elements
    #convention is <node name>, <positive node name>, <negative node name>, <optional voltage>
    circuit.C('load', 'vout', 'vss', u_F(capacitance))
    circuit.V('ss', 'vss', circuit.gnd, u_V(0))
    circuit.V('bias', 'vbias', circuit.gnd,u_V(Vbias))

    if not noise: #implement zero noise on source
        circuit.V('dd','vdd', circuit.gnd, u_V(Vdd))
    else: #implement random variation of source voltage
        circuit.RandomVoltageSource('dd','vdd', circuit.gnd,
                                    random_type='gaussian',
                                    duration=noise_duration,
                                    time_delay=noise_delay,
                                    parameter1=noise,
                                    parameter2=Vdd)

    #if vin is not 0 or None, it is a static voltage source
    if Vin:
        circuit.V('in', 'vin', circuit.gnd, u_V(Vin))
    else: #else, we connect vin to vout with a transmission line
        circuit.LosslessTransmissionLine('delay', 'vin', circuit.gnd, 'vout', circuit.gnd,
                impedance = impedance,
                time_delay = time_delay)

    #give mosfet elements
    circuit.MOSFET(1, 'vout', 'vin', 'vss', 'vss', model='nmos',
                l=l1, w=w1)
    circuit.MOSFET(2, 'vout', 'vbias', 'vdd', 'vdd', model='pmos',
                l=l2, w=w2)
    circuit.MOSFET(3, 'vdd', 'vin', 'vout', 'vss', model='nmos',
                l=l3, w=w3)

    return circuit

# Cell
def tup2ar(*t):
    '''
    Returns inclusive array 'x' of tuple 't' in (start,stop,step) format.
    '''
    s=(t[0],t[1]+t[2],t[2])
    x=np.arange(*s)
    #round to number of decimal places
    x=np.around(x,np.rint(abs(np.log10(t[-1]))).astype(int)+1)
    #cut off anything past bounds
    x=x[x<=t[1]]
    return x

# Cell
chaogate.Vin_tup=(0,1.2,0.01)
chaogate.Vin_ar=tup2ar(*chaogate.Vin_tup)
chaogate.Vin_slice=slice(*chaogate.Vin_tup)

# Cell
@sidis.timer
def sweep(*funcs,
          **kwargs : Optional[Dict[str,Union[float,tuple]]]
      ) -> Union[Dict[str,Array],Array]:
    '''

    Performs a dc analysis sweep of the input voltage `Vin`,

    and optionally over any tuples in `kwargs`. If any `kwargs`

    are not tuples, they are treated as circuit parameters for

    instantiation. If any of the `kwargs` tuples are keyed by

    `Vbias`, `Vdd`, or `TEMP`, they are calculated in a single

    sweep using the `simulator().dc` function call. Otherwise,

    the chaogate netlist is repeatedly instantiated over the

    changing parameters, and the simulator repeatedly called.

    Returns a `DataArray` for each `kwargs` containing `vout`

    dc function call, and coordinates of the sweeped array(s).

    If `funcs` is given, they are mapped over `vout` for each

    sweep, and added as coordinates to the returned `DataArray`.

    '''
    sweep_kwargs = {}
    static_kwargs = {}
    #partition kwargs into sweep vars and static vars
    for k,v in kwargs.items():
        if type(v) is tuple:
            sweep_kwargs[k]=v
        else:
            static_kwargs[k]=v
    #set default temperature
    if static_kwargs.get('TEMP') is not None:
        temp=static_kwargs['TEMP']
    else:
        temp=25
    #set default vin sweep if none given
    if sweep_kwargs.get('Vin') is None:
        Vin_slice=chaogate.Vin_slice
        Vin_ar=chaogate.Vin_ar
    else:
        Vin_tup=sweep_kwargs.pop('Vin')
        Vin_slice=slice(*Vin_tup)
        Vin_ar=tup2ar(*Vin_tup)

    if not sweep_kwargs: #only sweep vin
        cg=chaogate(**static_kwargs)
        f=cg.simulator(temperature=temp,nominal_temperature=25).dc
        vout=f(Vin=Vin_slice).vout
        coords=dict(Vin=Vin_ar)
        if funcs: #map functions as coordinates over data
            func_res={f.__name__:f(vout) for f in funcs}
            coords.update(func_res)
        return xr.DataArray(data=vout,
                            dims=['Vin'],
                            coords=coords,
                            name='vout'
                           )

    res=[] #otherwise we have tuples to sweep

    for k,s in sweep_kwargs.items():
        if k=='TEMP' or k=='Vbias' or k=='Vdd': #then sweep in 1 call
            cg=chaogate(**static_kwargs)
            f=cg.simulator(temperature=temp,nominal_temperature=25).dc
            vout=f(Vin=Vin_slice,**{k:slice(*s)}).vout
            coord=tup2ar(*s)
            vout=np.array(vout.reshape(( coord.size, Vin_ar.size )))
            res+=[xr.DataArray(data=vout,
                               dims=[k,'Vin'],
                               coords={k:coord,'Vin':Vin_ar},
                               name='vout'
                              )]
        else: #have to re-instantiate circuit and loop over attr
            coord=tup2ar(*s)
            res_k=np.empty((coord.size,Vin_ar.size))
            for i,c in enumerate(coord):
                new_static_kwargs=copy.copy(static_kwargs)
                new_static_kwargs.update({k:c})
                cg=chaogate(**new_static_kwargs)
                f=cg.simulator(temperature=temp,nominal_temperature=25).dc
                vout=f(Vin=Vin_slice).vout
                res_k[i]=np.array(vout)
            res+=[xr.DataArray(data=res_k,
                               dims=[k,'Vin'],
                               coords={k:coord,'Vin':Vin_ar},
                               name='vout'
                              )]

    if funcs: #map functions as coordinates over data
        for vout in res:
            func_res={f.__name__:(vout.dims[0],f(vout.data)) for f in funcs}
            vout.coords.update(func_res)

    if len(res)==1: #if only 1 sweep, just pass back xar
        res=res[0]

    return res

# Cell
@sidis.timer
@njit
def iterate_map(vout : Array[(Any, ...)],
                vin : Array[(Any)] = tup2ar(0,1.2,0.01),
                v0 : float = 0.45,
                N : int = 2000) -> Array[(2,...)]:
    '''
    Iterates the map given by `vout` = f(`vin`), `N` times.
    `vout` : [...,size(vin)] is an array of all the
    chaogate output voltages over the `vin` inputs.
    `v0` is the starting voltage. Returns an array
    `X` : [vout.shape[:-1],N,2] containing the
    map evaluations in the [...,0]th entry and the first
    derivatives in the [...,1] entry for each curve of `vout`.
    Note, if `vout.shape==vin.shape`, this will return an array
    of shape [1,vin.size,2].
    '''
    vo = vout.reshape((int(vout.size/vin.size),vout.shape[-1]))
    J = vo.shape[0]
    X=np.zeros((J,N,2))
    dv=vin[1]-vin[0]
    for j in range(J):
        xn=v0
        for i in range(N):
            X[j,i,0]=xn
            xn=np.interp(x=xn,xp=vin,fp=vo[j])
        X[j,:,1]=np.interp(x=X[j,:,0],xp=vin[:-1],fp=np.diff(vo[j]))/dv
    return X

# Cell
def iterate(res,
            v0 : float = 0,
            N : int = None) -> Array[(2,...)]:
    '''
    Uses `iterate_map` with a default iteration number
    corresponding to the length of the input array `vout`,
    and reshapes according to this length. njit is unable
    to do this, so we use two functions.
    '''
    if N is None:
        N=res.Vin.shape[-1]
    X = iterate_map(res.data,res.Vin.data,v0,N)
    dims = list(res.dims)
    if len(dims)==1:
        dims = []
    else:
        dims = dims[:-1]
    dims += ['Iterations','Derivative']
    return xr.DataArray(data=X.reshape(*res.shape[:-1],*X.shape[-2:]),
                        dims=dims,
                        coords={k:v for k,v in res.coords.items() if k!='Vin'},
                        name='iterate'
                       )

# Cell
def lyapunov(x : Array[Any,...], replace_zeros_with : Union[int,float] = 0.01):
    '''
    Returns average Lyapunov exponent of array 'x'.
    Replaces zeros with `replace_zeros_with` to
    calculate log correctly.
    '''
    if isinstance(x,xr.DataArray): #assume iterate map
        y=np.abs(x.data[...,1],dtype=np.float64)
    else:
        y=np.abs(x,dtype=np.float64)
    y[y==0]=replace_zeros_with
    y=np.log(y)
    y=np.mean(y,axis=-1)
    if not isinstance(x,xr.DataArray):
        return y
    else:
        return xr.DataArray(data=y,
                            dims=list(x.dims)[:-2],
                            coords=x.coords,
                            name='lyapunov'
                           )

# Cell
@sidis.timer
def grid(**kwargs):
    '''
    Like 'sweep', but over all combinations of the `kwargs` tuples.
    Returns a `kwargs`-dimensional hybercube ranging over all the
    supplied tuples, in the form of an `xarray.DataArray` object.
    '''
    #partition kwargs into loops and static attrs
    if kwargs.get('Vin') is None:
        Vin = chaogate.Vin_tup
    else:
        Vin = kwargs.get('Vin')

    sweep_kwargs = {'Vin':Vin}
    static_kwargs = {}
    for k,v in kwargs.items():
        if type(v) is tuple:
            sweep_kwargs[k]=v
        else:
            static_kwargs[k]=v

    #sort loops by giving order of attrs; placing sweeps as inner loops
    key={kwarg:3 for kwarg in kwargs}
    key['Vin']=-1
    key['Vbias']=0
    key['Vdd']=1
    key['TEMP']=2
    #get number of inner loops for callable dc args; iterate over rest
    n_inner_loops = 2 if ('Vbias' in sweep_kwargs or 'Vdd' in sweep_kwargs \
                          or 'TEMP' in sweep_kwargs) else 1
    #print(n_inner_loops)
    sweep_kwargs=list(sweep_kwargs.items())
    sweep_kwargs.sort(key=lambda t:key[t[0]],reverse=True)

    #get dict of inner slice for dc function call
    inner_slice={sweep_kwargs[-n_inner_loops][0]:slice(*sweep_kwargs[-n_inner_loops][1])}
    sweep_kwargs=dict(sweep_kwargs)

    #get coordinates as dict of arrays for every sweep
    coords={k:tup2ar(*v) for k,v in sweep_kwargs.items()}

    #get sizes of array
    sizes=[c.size for c in coords.values()]

    #create array holding output of dc function calls over grid of coords
    arr=np.zeros(tuple(sizes))

    #truncate coords up to inner value for function calls
    static_arg_list=list(coords.items())[:-n_inner_loops]

    #loop over ndindex of outer loops, call inner as sweep
    #use tqdm as progress bar, give total length of outer loop
    for s in tqdm(np.ndindex(arr.shape[:-n_inner_loops]),
                  total=np.prod(arr.shape[:-n_inner_loops])):

        #index static args and feed to chaogate netlist
        static_args={k:v[s[i]] for i,(k,v) in enumerate(static_arg_list)}
        circuit=chaogate(**static_args)

        #get temperature of current sweep
        if static_args.get('TEMP') is None:
            temp=25
        else:
            temp=static_args.get('TEMP')

        #perform sweep, feed to array
        f=circuit.simulator(temperature=temp,nominal_temperature=25).dc
        vout=f(Vin=slice(*Vin),**inner_slice).vout
        arr[s]=np.array(vout.reshape(( arr.shape[-2], arr.shape[-1] )))

    #return as xar object containing coords and any func calls
    res=xr.DataArray(data=arr,dims=list(coords),coords=coords,name='vout')

    return res

# Cell
def bifurcate(res=None,
              v0=0,
              T=500,
              N=1000,
              as_grid=False,
              **kwargs):
    '''
    Creates a bifurcation of the system about the given parameters.

    If `as_grid`, the result is assumed to be evaluated over a grid;

    else, a `sweep` is assumed. If `res` is None, it is evaluated over

    `kwargs`. Iterates the resulting system `res` N times starting from

    `v0` using `iterate`, discarding the transient specified by the first

    `T` points. Calculates the `lyapunov` exponent over the iterated map,

    and returns a `xarray.Dataset`. If not `as_grid`, the dataset has

    a different variable for each of the specified `kwargs` sweeps; else,

    there is a single variable for `vout`, `lyapunov`, and `iterate`.

    Example use:

        bifurcate(
            Vbias = (0,1.2,0.01),
            Vdd = (1.1,1.3,0.1),
            TEMP = (20,30,5),
            as_grid = True
        )

    '''
    if not as_grid:
        if res is None:
            res=sweep(**kwargs)

        if not isinstance(res,list):
            res=[res]
        coords={'Vin':res[0].Vin}
        coords.update({r.dims[0]:r.coords[r.dims[0]] for r in res})
        ds=xr.Dataset(data_vars={'vout_'+r.dims[0]:(r.dims,r) for r in res},
                     coords=coords)
        for k,v in ds.data_vars.items():
            itr=iterate(v,N=N,v0=v0)
            lya=lyapunov(itr[...,T:,:])
            ds.update({
                'iterate_'+k[5:]:([v.dims[0],'Iterations'],itr[...,0]),
                'lyapunov_'+k[5:]:(v.dims[0],lya)
            })
    else:
        if res is None:
            res=grid(**kwargs)
        ds=res.to_dataset()
        itr=iterate(res,N=N,v0=v0)
        lya=lyapunov(itr[...,T:,:])
        ds.update(dict(lyapunov=(list(res.dims)[:-1],lya),
                       iterate=(list(res.dims)[:-1]+['Iterations'],itr[...,0])
                      )
                 )

    return ds

# Cell
@njit
def booleanize_ar(vn, threshold=None):
    '''
    Convert the numpy array `vn` into a bitstream
    according to `threshold`; values of `vn>=threshold`
    will be set to `1`, and values of `vn<threshold`
    will be set to `0`. If `threshold` is not supplied,
    it defaults to halfway between the range of `vn`.
    '''
    if threshold is None:
        threshold=(np.max(vn)-np.min(vn))/2
    B=np.empty(vn.shape)
    for s in np.ndindex(vn.shape):
        if vn[s]>=threshold:
            B[s]=1
        else:
            B[s]=0
    return B

# Cell
def booleanize(vn, threshold=None):
    '''
    Like `booleanize_ar`, but with typecasting
    for `xarray.DataArray` inputs.
    '''
    if isinstance(vn,xr.DataArray):
        B=booleanize_ar(vn.data,threshold)
        return vn.copy(deep=False,data=B)
    else:
        return booleanize_ar(vn,threshold)

# Cell
def boolean_gradient(vn , threshold=None, dimensions_up_to=-1):
    '''
    Compute the `booleanize`d gradient of the
    iterated map `vn`.
    '''
    B = booleanize(vn,threshold)
    axes = tuple([i for i,s in enumerate(B.shape[:dimensions_up_to])])
    grad = np.gradient(B,axis=axes)
    if not isinstance(grad,list):
        grad = list(grad)
    grad = np.array(grad)
    return grad

# Cell
def boolean_divergence(grad , N=-1, normalize=False):
    '''
    Compute the divergence of the absolute value of the
    `boolean_gradient` `grad` after `N` iterations.
    If `normalize`, divide the result by the max.
    '''
    #first get hamming distances over iterations
    div = np.mean(np.abs(grad[...,:N]),axis=-1)
    #now average over each matrix derivative direction
    div = np.mean(div,axis=0)
    if normalize:
        div /=np.max(div)
    return div