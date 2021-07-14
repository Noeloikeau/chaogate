# AUTOGENERATED! DO NOT EDIT! File to edit: 01_plotting.ipynb (unless otherwise specified).

__all__ = ['format_equality', 'format_label', 'axes', 'sample_ar', 'plot_sweep', 'plot_bifurcate']

# Cell
from chaogate import *

# Cell
axes={'TEMP':dict(label=r'$T$',unit=r'($^\circ$C)',scale=1),
     'Vin':dict(label=r'$V_{in}$',unit=r'$(V)$',scale=1),
     'vout':dict(label=r'$V_{out}$',unit=r'$(V)$',scale=1),
     'Vdd':dict(label=r'$V_{DD}$',unit=r'$(V)$',scale=1),
     'Vbias':dict(label=r'$V_{bias}$',unit=r'$(V)$',scale=1),
     'Iterations':dict(label=r"$\{V_{n}\}$",unit=r'$(V)$',scale=1),
     'w1' : dict(label=r"$W_{1}$",unit=r'$(nm)$',scale=1e9),
     'w2' : dict(label=r"$W_{2}$",unit=r'$(nm)$',scale=1e9),
     'w3' : dict(label=r"$W_{3}$",unit=r'$(nm)$',scale=1e9),
     'l1' : dict(label=r"$L_{1}$",unit=r'$(nm)$',scale=1e9),
     'l2' : dict(label=r"$L_{2}$",unit=r'$(nm)$',scale=1e9),
     'l3' : dict(label=r"$L_{3}$",unit=r'$(nm)$',scale=1e9),
     'capacitance' : dict(label=r"$Capacitance$",unit=r"$(fF)$",scale=1e15),
     'noise' : dict(label=r"$Noise$",unit=r'$(V)$',scale=1)}

def format_equality(var, #axes variable
                    val):
    if isinstance(val,xr.DataArray):
        val=val.data
    name = var.name
    dic = axes[name]
    return f"{dic['label']} = {val*dic['scale']} {dic['unit']}"

def format_label(var):
    return f"{axes[var.name]['label']} {axes[var.name]['unit']}"

# Cell
def sample_ar(x,N=4):
    '''
    Takes 'N' even samples from array 'x', returning values and indices.
    '''
    I=np.round(np.linspace(0, len(x) - 1, N)).astype(int)
    return x[I]

# Cell
def plot_sweep(s,
               title = r'Chaogate Transfer Function',
               ncurves = 5,
               fontsize = 20):
    '''
    Plots the voltage sweep vin-vout curves for different parameters.
    '''
    vin,vout,var=s.Vin,s,getattr(s,s.dims[0])
    var = sample_ar(var,ncurves)
    figure, ax = plt.subplots()
    figure.set_figheight(5)
    for v in var:
        ax.plot(vin,vout.sel(**{var.name:v}),label=format_equality(var,v))

    ax.set_title(title,fontsize=fontsize)
    ax.grid()
    ax.legend(fontsize=14,bbox_to_anchor=(1,1), loc="upper left", frameon=False)
    xticks = sample_ar(vin,4).data
    xlabels = str([s for s in xticks])

    ax.set_xlabel(format_label(vin),fontsize=fontsize)
    ax.set_ylabel(format_label(vout),fontsize=fontsize)

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticks,fontsize=fontsize)
    ax.set_yticks(xticks)
    ax.set_yticklabels(xticks,fontsize=fontsize)
    ax.tick_params(axis='y',size=fontsize)
    ax.set_aspect('equal')
    plt.show()

# Cell
def plot_bifurcate(itr,lya,fontsize=20, ticksize=15, title='', T=50):
    '''
    if kwargs is not None:
        data = ds.sel(**kwargs)
    else:
        data=ds
    dims=[d for d in data.coords if data.coords[d].shape!=() and d!='Vin']
    coords=[data.coords[d] for d in dims]
    itrs = set([k for k,s in data.data_vars.items() for d in dims
                if 'iterate' in k and d in s.dims])
    lyas = set([k for k,s in data.data_vars.items() for d in dims
                if 'lyapunov' in k and d in s.dims])
    itrs = [data.data_vars[i] for i in itrs]
    lyas = [data.data_vars[i] for i in lyas]'''

    fig, ax = plt.subplots()
    fig.subplots_adjust(right=0.75)
    for i,(x,y) in enumerate(zip(getattr(itr,itr.dims[0]).data, itr.data[...,T:])):
        color='tab:red' if lya.data[i]>0 else 'tab:blue'
        ax.scatter([x] * len(y), y, s=.1, color=color)

    ax.set_xlabel(f'{format_label(getattr(itr,itr.dims[0]))}',color='black',fontsize=fontsize)
    ax.set_ylabel(r"$V_{n}$",color='black',fontsize=fontsize)

    ax.tick_params(axis='y', labelcolor='black',labelsize=ticksize)
    ax.tick_params(axis='x', labelcolor='black',labelsize=ticksize)

    fig.suptitle(title,fontsize=fontsize)

    plt.show()