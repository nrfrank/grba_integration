import sys
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

from ctypes import *
from scipy.optimize import root, fsolve, brentq
from scipy.integrate import nquad, quad, romberg, quadrature
from math import radians, degrees
from cycler import cycler

from grba_int import *

# n = 10
# colors = [plt.get_cmap('Blues')(1. * i/n) for i in range(n)]
# mpl.rcParams['axes.prop_cycle'] = cycler('color', colors)
# mpl.rcParams['axes.prop_cycle'] = cycler('color', ['r', 'g', 'b'])
# mpl.rcParams['image.cmap']='Blues'
# mpl.rcParams['axes.prop_cycle'] =  cycler('color', ['#b1c4e2', '#1f57a2', '#1e477b', '#062a5a', '#161928'])
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = 'Helvetica Neue UltraLight'
mpl.rcParams['font.variant'] = 'small-caps'
mpl.rcParams['font.size'] = 21
mpl.rcParams['axes.labelsize'] = 13
mpl.rcParams['axes.titlesize'] = 11
mpl.rcParams['xtick.labelsize'] = 9
mpl.rcParams['ytick.labelsize'] = 9
mpl.rcParams['legend.fontsize'] =7
mpl.rcParams['figure.titlesize'] = 17
mpl.rcParams['legend.numpoints'] = 1

# plt.style.use('seaborn-whitegrid')
sns.set_style('ticks', {'legend.frameon': True})

TINY = 1.0e-9

grbaint = cdll.LoadLibrary("Release/grba_integration.dll")
phiInt = grbaint.phiInt
phiInt.restype = c_double
phiInt.argtypes = [c_double, c_double, c_double, c_double]
thp = grbaint.thetaPrime
thp.restype = c_double
thp.argtypes = [c_double, c_double, c_double]
engProf = grbaint.energyProfile
engProf.restype = c_double
engProf.argtypes = [c_double, c_double, c_double]
fluxG_cFunc = grbaint.fluxWrap
fluxG_cFunc.restype = c_double
fluxG_cFunc.argtypes = [c_double, c_double, c_double, c_double, c_double, c_double, c_double, c_double]

def intG(y, chi, k = 0.0, p = 2.2):
    bG = (1.0 - p)/2.0
    ys = np.power(y, 0.5*(bG*(4.0 - k) + 4.0 - 3.0*k))
    chis = np.power(chi, np.divide(7.0*k - 23.0 + bG*(13.0 + k), 6.0*(4.0 - k)))
    factor = np.power((7.0 - 2.0*k)*chi*np.power(y, 4.0 - k) + 1.0, bG - 2.0)
    return ys*chis*factor

def fluxG(y, chi, k = 0.0, p = 2.2):
    Ck = (4.0 - k)*np.power(5.0 - k, np.divide(k - 5.0, 4.0 - k))
    cov = np.divide(np.power(y, 5.0 - k), 2.0*Ck)
    return 2.0*np.pi*cov*intG(y, chi, k, p)

def thetaPrime(r, thv, phi):
    # top = r*(np.cos(thv)**2.0 - 0.25*np.sin(2.0*thv)**2.0*np.cos(phi)**2.0)**0.5
    # bot = 1.0 + 0.5*r*np.sin(2.0*thv)*np.cos(phi)
    # return np.divide(top, bot)
    return thp(r, thv, phi)

def r0_max(y, kap, sig, thv, gA = 1.0, k = 0.0, p = 2.2):
    Gk = (4.0 - k)*gA**2.0
    def rootR0(rm):
        thP0 = thetaPrime(rm, thv, 0.0)
        rExp = -np.power(np.divide(thP0, sig), 2.0*kap)
        lhs = np.divide(y - np.power(y, 5.0 - k), Gk)
        rhs = (np.tan(thv) + rm)**2.0*np.exp2(rExp)
        return rhs - lhs

    rootValR0 = fsolve(rootR0, 1.0e-5)[0]
    # rootValR0 = brentq(root, 0.0, 0.6)
    return rootValR0

def root_fun(r, r0, phi, kap, sig, thv):
    thp = thetaPrime(r, thv, phi)
    eng = engProf(thp, sig, kap)
    lhs = eng*(np.power(r, 2.0) + 2.0*r*np.tan(thv)*np.cos(phi) + np.power(np.tan(thv), 2.0))
    thp0 = thetaPrime(r, thv, 0.0)
    eng0 = engProf(thp0, sig, kap)
    rhs = np.power(r0 + np.tan(thv), 2.0)*eng0
    return lhs - rhs

def root_jac(r, r0, phi, kap, sig, thv):
    thp = thetaPrime(r, thv, phi)
    first = r + np.tan(thv)*np.cos(phi)
    second = np.power(r, 2.0) + 2.0*r*np.tan(thv)*np.cos(phi) + np.power(np.tan(thv), 2.0)
    frac = (kap*np.log(2.0)*np.power(thp / sig, 2.0*kap)) / (r*(1.0 + 0.5*r*np.sin(2.0*thv)*np.cos(phi)))
    exponent = 2.0*engProf(thp, sig, kap)
    return (first - second*frac)*exponent

def solveR(g, r0, phi, kap, sig, thv):
    return root(root_fun, g, args = (r0, phi, kap, sig, thv)).x[0]
    # return root(root_fun, g, args = (r0, phi, kap, sig, thv), jac=root_jac).x[0]

def phiUpperBound(r0, kap, sig, thv):
    s = np.frompyfunc(solveR, 5, 1)
    R0P_MAX = s(r0, np.pi, kap, sig, thv)
    return R0P_MAX

def test_rmax():
    R0 = 0.1
    PHI = radians(180.0)
    SIGMA = 2.0
    for KAPPA in [0.0, 1.0, 10.0]:
        for THV in [0.0, 2.0, 6.0]:
            THETA_V = radians(THV)
            sol = solveR(R0, R0, PHI, KAPPA, SIGMA, THETA_V)
            print KAPPA, THV, sol

def r_max(phi, r0, kap, sig, thv):
    def rootR(r):
        thp = thetaPrime(r, thv, phi)
        eng = engProf(thp, sig, kap)
        lhs = eng*(np.power(r, 2) + 2.0*r*np.tan(thv)*np.cos(phi) + np.power(np.tan(thv), 2))
        thp0 = thetaPrime(r, thv, 0.0)
        eng0 = engProf(thp0, sig, kap)
        rhs = np.power(r0 + np.tan(thv), 2)*eng0
        return lhs - rhs

    rootValR = fsolve(rootR, r0)[0]
    return rootValR

def r0_max_val(r, y, kap, sig, thv, gA = 1.0, k = 0.0, p = 2.2):
    Gk = (4.0 - k)*gA**2.0
    thP0 = thetaPrime(r, thv, 0.0)
    rExp = -np.power(np.divide(thP0, sig), 2.0*kap)
    lhs = np.divide(y - np.power(y, 5.0 - k), Gk)
    rhs = (np.tan(thv) + r)**2.0*np.exp2(rExp)
    return rhs - lhs

vec_r0Max_val = np.vectorize(r0_max_val)

def fluxG_fullStr(r, y, kap, sig, thv, gA = 1.0, k = 0.0, p = 2.2):
    Gk = (4.0 - k)*gA**2.0
    thP0 = thetaPrime(r, thv, 0.0)
    exp0 = np.power(np.divide(thP0, sig), 2.0*kap)
    chiVal = np.divide(y - Gk*np.exp2(-exp0)*(np.tan(thv) + r)**2.0, np.power(y, 5.0 - k))
    # if chiVal < 1.0:
        # return 0.0
    # else:
        # return r*intG(y, chiVal)*phiInt(r, kap, thv, sig)
    try:
        return r*intG(y, chiVal)*phiInt(r, kap, thv, sig)
    except WindowsError as we:
        print kap, thv, y, r, intG(y, chiVal), we.args[0]
    except:
        print "Unhandled Exception"

vec_fluxG_fullStr = np.vectorize(fluxG_fullStr)

def fluxG_fullStr_cFunc(r, y, kap, sig, thv, gA = 1.0, k = 0.0, p = 2.2):
    try:
        return fluxG_cFunc(y, r, kap, sig, thv, gA, k, p)
    except WindowsError as we:
        print we.args[0]
    except:
        print "Unhandled Exception"

vec_fluxG_fullStr_cFunc = np.vectorize(fluxG_fullStr_cFunc)

def bounds_yr(kap, sig, thv):
    return [TINY, 1.0]

def bounds_ry(y, kap, sig, thv):
    R0MAX = r0_max(y, kap, sig, thv)
    if R0MAX < 0.0:
        return [0.0, 0.0]
    else:
        return [0.0, R0MAX]

def plot_r0Int(y, kap, sig, thv):
    R0_MAX = r0_max(y, kap, sig, thv)
    if R0_MAX > 0.0:
        r0s = np.linspace(0.0, R0_MAX, num = 100)
        # r0s = np.logspace(-3, np.log10(R0_MAX), num = 100)
        vals = vec_fluxG_fullStr(r0s, y, kap, sig, thv)
        dat = pd.DataFrame(data = {'r0': r0s, 'int': vals})
        NUM_ROWS = len(dat)
        dat['y'] = np.repeat(y, NUM_ROWS)
        dat['kap'] = np.repeat(kap, NUM_ROWS)
        dat['thv'] = np.repeat(thv, NUM_ROWS)
        # print data.head()
        return(dat)

def plot_r0Int_cTest(y, kap, sig, thv):
    R0_MAX = r0_max(y, kap, sig, thv)
    if R0_MAX > 0.0:
        r0s = np.logspace(-3, np.log10(R0_MAX), num = 100)
        vals = vec_fluxG_fullStr(r0s, y, kap, sig, thv)
        cVals = vec_fluxG_fullStr_cFunc(r0s, y, kap, sig, thv)
        lab = np.repeat("Python", len(vals))
        clab = np.repeat("C++", len(cVals))
        dat = pd.DataFrame(data = {'r0': r0s, 'int': vals, 'lab': lab})
        cdat = pd.DataFrame(data = {'r0': r0s, 'int': cVals, 'lab': clab})
        full_dat = pd.concat([dat, cdat])
        NUM_ROWS = len(full_dat)
        full_dat['kap'] = np.repeat(kap, NUM_ROWS)
        full_dat['thv'] = np.repeat(degrees(thv), NUM_ROWS)

        return(full_dat)

def plot_r0Max(y, kap, sig, thv):
    r0s = np.linspace(0.0, 1.0, num = 100)
    vals = vec_r0Max_val(r0s, y, kap, sig, radians(thv))
    dat = pd.DataFrame(data = {'r0': r0s, 'int': vals})
    NUM_ROWS = len(dat)
    dat['y'] = np.repeat(y, NUM_ROWS)
    dat['kap'] = np.repeat(kap, NUM_ROWS)
    dat['thv'] = np.repeat(thv, NUM_ROWS)
    # max_val = r0_max(y, kap, sig, thv)
    # dat['r0max'] = np.repeat(max_val, NUM_ROWS)
    # dat['maxval'] = np.repeat(0.0, NUM_ROWS)
    return(dat)

def plot_r0Int_grid_cTest(y):
    SIGMA = 2.0
    # YVAL = TINY
    df_list = []
    for i, KAPPA in enumerate([0.0, 1.0, 10.0]):
        for j, THETA_V in enumerate([0.0, 2.0, 6.0]):
            print KAPPA, THETA_V
            df = plot_r0Int_cTest(y, KAPPA, SIGMA, radians(THETA_V))
            df_list.append(df)

    data = pd.concat(df_list)
    print data
    grid = sns.lmplot(x = 'r0', y = 'int', hue = 'lab',
                        col = 'kap', row = 'thv', data = data, markers = 'o',
                        palette = 'viridis', fit_reg = False)
    grid.set(yscale="log")
    grid.set(xscale="log")
    axes = grid.axes
    # axes[0, 0].set_ylim(1.0e-9, )
    axes[0, 0].set_xlim(1.0e-3, )
    plt.show()

def plot_r0Int_grid():
    SIGMA = 2.0
    df_list = []
    # max_list = [[[] for x in range(3)] for y in range(3)]
    # i = 0
    for i, KAPPA in enumerate([0.0, 1.0, 10.0]):
        for j, THETA_V in enumerate([0.0, 2.0, 6.0]):
            for y in [TINY, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0 - TINY]:
            # for y in [TINY, 1.0 - TINY]:
                # print KAPPA, THETA_V, y
                df = plot_r0Int(y, KAPPA, SIGMA, radians(THETA_V))
                # df = plot_r0Max(y, KAPPA, SIGMA, THETA_V)
                # print df.head()
                df_list.append(df)

                # max_val = r0_max(y, KAPPA, SIGMA, radians(THETA_V))
                # max_list[j][i].append(max_val)
                # print KAPPA, THETA_V, y, max_val
            # i += 1

    data = pd.concat(df_list)
    # print data.head()
    # plt.figure()
    grid = sns.lmplot(x = 'r0', y = 'int', hue = 'y',
                        col = 'kap', row = 'thv', data = data, markers = '.',
                        palette = 'viridis', fit_reg = False)  #
    # grid.map(plt.axhline, color = 'red', linestyle = '--')
    # grid.map(plt.scatter, 'r0max', 'maxval')
    grid.set(yscale="log")
    # grid.set(xscale="log")
    # grid.set_axis_labels("r0'", "Root Function")
    grid.set_axis_labels("r0'", "r0' Integrand")

    # for loc, data in grid.facet_data():
        # # print loc
        # grid.axes[loc[0], loc[1]].scatter(max_list[loc[0]][loc[1]], [0.0 for x in range(7)], marker = 'o')
    axes = grid.axes
    # for i, ax in enumerate(axes.flat):
        # print i, ax.get_xlim()
        # for rm in max_list[i]:
            # ln_ = ax.axvline(x = rm, linestyle = '--', color = 'red')

    axes[0, 0].set_ylim(1.0e-9, )
    axes[0, 0].set_xlim(0.0, )
    grid.set_titles('thv = {row_name} | kap = {col_name}')
    plt.show()
    # grid.savefig("r0-Int.png")

def plot_r0Int_time(y, kap, sig, thv, r0min):
    ys = np.linspace(0.0, 1.0, num = 10)
    vals = vec_fluxG_fullStr(r0s, y, kap, sig, thv)
    dat = pd.DataFrame(data = {'r0': r0s, 'int': vals})
    NUM_ROWS = len(dat)
    dat['y'] = np.repeat(y, NUM_ROWS)
    dat['kap'] = np.repeat(kap, NUM_ROWS)
    dat['thv'] = np.repeat(thv, NUM_ROWS)
    # print data.head()
    return(dat)
    
def plot_r0IntTime_grid():
    SIGMA = 2.0
    df_list = []
    for i, KAPPA in enumerate([0.0, 1.0, 10.0]):
        for j, THETA_V in enumerate([0.0, 2.0, 6.0]):
            for y in [TINY, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0 - TINY]:
                df = plot_r0Int(y, KAPPA, SIGMA, radians(THETA_V))
                # df = plot_r0Max(y, KAPPA, SIGMA, THETA_V)
                # print df.head()
                df_list.append(df)

                # max_val = r0_max(y, KAPPA, SIGMA, radians(THETA_V))
                # max_list[j][i].append(max_val)
                # print KAPPA, THETA_V, y, max_val
            # i += 1

    data = pd.concat(df_list)
    # print data.head()
    # plt.figure()
    grid = sns.lmplot(x = 'r0', y = 'int', hue = 'y',
                        col = 'kap', row = 'thv', data = data, markers = '.',
                        palette = 'viridis', fit_reg = False)  #
    # grid.map(plt.axhline, color = 'red', linestyle = '--')
    # grid.map(plt.scatter, 'r0max', 'maxval')
    grid.set(yscale="log")
    # grid.set(xscale="log")
    # grid.set_axis_labels("r0'", "Root Function")
    grid.set_axis_labels("r0'", "r0' Integrand")

    # for loc, data in grid.facet_data():
        # # print loc
        # grid.axes[loc[0], loc[1]].scatter(max_list[loc[0]][loc[1]], [0.0 for x in range(7)], marker = 'o')
    axes = grid.axes
    # for i, ax in enumerate(axes.flat):
        # print i, ax.get_xlim()
        # for rm in max_list[i]:
            # ln_ = ax.axvline(x = rm, linestyle = '--', color = 'red')

    axes[0, 0].set_ylim(1.0e-9, )
    axes[0, 0].set_xlim(0.0, )
    grid.set_titles('thv = {row_name} | kap = {col_name}')
    plt.show()
    # grid.savefig("r0-Int.png")

def r0_integral():
    SIG = 2.0
    dat_list = []
    for i, KAP in enumerate([0.0, 1.0, 10.0]):
        for j, THETA_V in enumerate([0.0, 2.0, 6.0]):
            THV = radians(THETA_V)
            ys = np.linspace(0.0, 1.0, 100)
            ints = np.zeros(len(ys))
            for index in range(len(ys)):
                YVAL = ys[index]
                R0_MAX = r0_max(YVAL, KAP, SIG, THV)
                if R0_MAX > 0.0:
                    int_val = quad(fluxG_fullStr, 0.0, R0_MAX,
                                    args = (YVAL, KAP, SIG, THV),
                                    epsabs = 1.0e-5)[0]
                    print KAP, THETA_V, YVAL, int_val
                    ints[index] = int_val

            loc_df = pd.DataFrame(data = {'y': ys, 'ival': ints})
            N = len(loc_df)
            loc_df['kap'] = np.repeat(KAP, N)
            loc_df['thv'] = np.repeat(THETA_V, N)

            dat_list.append(loc_df)

    df = pd.concat(dat_list)
    grid = sns.lmplot(x = 'y', y = 'ival', col = 'kap', row = 'thv', data = df,
                        fit_reg = False)
    plt.show()

def plot_rMaxPhi_grid(y, kap, sig, thv):
    R0_MAX = r0_max(y, kap, sig, thv)
    # r0s = np.linspace(0.1, R0_MAX, num = 100)
    # r0s[0] += TINY
    r0s = np.linspace(R0_MAX, 0.0, endpoint = False, num = 100)
    phis = np.linspace(0.0, 2.0*np.pi, num = 100)
    # vec_r_max = np.vectorize(r_max)
    # rs = vec_r_max(phis, r0s, kap, sig, thv)
    R, P = np.meshgrid(r0s, phis)
    # RM = vec_r_max(P, R, kap, sig, thv)
    s = np.frompyfunc(solveR, 5, 1)

    RM = np.abs(s(R, P, kap, sig, thv))
    # print RM
    RNORM = np.power(np.divide(RM, r0s), 2.0)
    # df = pd.DataFrame(data = {'r0': r0s, 'phi': phis, 'r': rs})
    # df_piv = df.pivot(index = 'phi', columns = 'r0', values = 'r')
    # print df_piv.head()
    df = pd.DataFrame(data = RM, index = np.round(np.divide(phis, np.pi), decimals = 3), columns = np.round(r0s, decimals = 3))
    df = df[df.columns].astype(float)
    # print df.head()
    ax = sns.heatmap(df, xticklabels = 10, yticklabels = 25, robust = True)
    ax.invert_xaxis()
    ax.invert_yaxis()
    plt.xticks(rotation = 90)
    plt.show()
    plt.clf()

    # plt.figure()
    # plt.pcolormesh(R, P, RM)
    # plt.show()

def plot_r0Phi(r0, kap, sig, thv):
    s = np.frompyfunc(solveR, 5, 1)
    phis = np.linspace(0.0, 2.0*np.pi, 100)
    vals = np.power(np.divide(s(r0, phis, kap, sig, thv), r0), 2.0)
    dat = pd.DataFrame(data = {'phi': r0s, 'fPhi': vals})
    NUM_ROWS = len(dat)
    dat['y'] = np.repeat(y, NUM_ROWS)
    dat['kap'] = np.repeat(kap, NUM_ROWS)
    dat['thv'] = np.repeat(thv, NUM_ROWS)
    # print data.head()
    return(dat)

def plot_root_grid():
    R0 = np.power(10.0, -9.0)
    PHI = np.pi/2.0
    SIG = 2.0
    # for YVAL in [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]:
    for YVAL in [0.5]:
        js = []
        fs = []
        ps = []
        rs = []
        ks = []
        ts = []
        cs = []
        for KAP in [0.0, 1.0, 10.0]:
            for THV in [1.0, 2.0, 6.0]:
                THETA_V = radians(THV)
                phis = np.linspace(0.0, 2.0*np.pi, num = 5)
                # phiVal = np.pi/2.0
                # phis = [phiVal - R0, phiVal, phiVal + R0, 3.0*phiVal - R0, 3.0*phiVal, 3.0*phiVal + R0]
                for c, PHI in enumerate(phis):
                # r0s = [1.0e-9, 1.0e-7, 1.0e-5, 1.0e-3, 1.0e-1]
                # r0s = [1.0e-9, 1.0e-7]
                # for c, R0 in enumerate(r0s):
                    # G = R0
                    rVals = np.linspace(-100.0*R0, 100.0*R0, num = 100)
                    # rVals = np.linspace(-0.1, 0.1, num = 100)
                    for R in rVals:
                        jac = root_jac(r=R, r0=R0, phi=PHI, kap=KAP, sig=SIG, thv=THETA_V)
                        fun = root_fun(r=R, r0=R0, phi=PHI, kap=KAP, sig=SIG, thv=THETA_V)
                        js.append(jac)
                        fs.append(fun)
                        ps.append(PHI/np.pi)
                        # ps.append(R0)
                        rs.append(R)
                        ks.append(KAP)
                        ts.append(THV)
                        cs.append(c)

        data = [ps, rs, ks, ts, js, fs, cs]
        df = pd.DataFrame(data)
        df = df.transpose()
        cols = ['R0', 'Rp', 'Kappa', 'ThetaV', 'Jac', 'Fun', 'C']
        df.columns = cols
        # df = df.round({'R0P': 3})
        g = sns.FacetGrid(df, col='Kappa', row='ThetaV', hue='C',
                                palette = sns.color_palette("deep", n_colors=5)) #ylim=(0,2),
        # g.map(plt.plot, "Rp", "Jac", lw = 1, linestyle='dashed')
        g.map(plt.plot, "Rp", "Fun", lw = 1)
        # g = sns.factorplot(x="Phi", y="FPhi", hue="C", row="ThetaV", col="Kappa",
                            # data=df, palette = sns.color_palette("Blues", n_colors=len(r0s)))
        # g.set_axis_labels(r"$\phi [\pi]$", r"$Log f^2(\phi) = Log (r'/r_0')^2$")
        for i in range(len(g.fig.get_axes())):
            handles, labels = g.fig.get_axes()[i].get_legend_handles_labels()
            thv_val = float(g.fig.get_axes()[i].get_title().split('|')[0].split('=')[1].strip())
            kap_val = float(g.fig.get_axes()[i].get_title().split('|')[1].split('=')[1].strip())
            # print kap_val, thv_val
            labs = ['{:.2e}'.format(df.groupby(['Kappa', 'ThetaV', 'C'])
                                    .get_group((kap_val, thv_val, float(lab)))['R0']
                                    .unique()[0]) for lab in labels]
            g.fig.get_axes()[i].legend(handles, labs,
                                                loc='upper right',
                                                bbox_to_anchor=(1.2, 1.0))
        g.set_titles(r"$\kappa = {col_name}$ | $\theta_V = {row_name}$")
        plt.suptitle(r"$y={a} | r'_{{0}}={b}$".format(a=YVAL, b=R0))
        g.fig.subplots_adjust(top=.9)
        plt.show()

def main(tiny):
    # tiny = np.power(10.0, -3.0)
    SIGMA = 2.0
    # KAPPA = 0.0
    # THETA_V = radians(2.0)
    # YVAL = 0.05
    # plt.figure()
    # for YVAL in [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]:
    for YVAL in [0.5]:
        ps = []
        fs = []
        rs = []
        ks = []
        ts = []
        cs = []
        for KAP in [0.0, 1.0, 10.0]:
            for THV in [1.0, 2.0, 6.0]:
                THETA_V = radians(THV)
                R0MAX = r0_max(YVAL, KAP, SIGMA, radians(THV))
                # r0s = np.linspace(0.0, R0MAX, num = 9)
                # r0s[0] = tiny
                r0s = [1.0e-5]  # , 1.0e-7, 1.0e-9
                phis = np.linspace(0.0, 2.0*np.pi, num = 100)
                # R, P = np.meshgrid(r0s, phis)
                # s = np.frompyfunc(solveR, 5, 1)
                # RM = s(R, P, KAP, SIGMA, radians(THV))
                # r0Maxs = np.amax(RM, axis = 1)
                # r0Maxs = phiUpperBound(r0s, KAP, SIGMA, radians(THV))
                # plt.plot(r0s, r0Maxs, label = "kap = {a: 04.1f}, thv = {b: 3.1f}".format(a = KAP, b = THV))
                # plt.legend()
                # vals = np.linspace(R0MAX, 0.0, endpoint = False, num = 100, retstep = True)
                # print KAP, THV, R0MAX, vals[1], vals[0]
                # plot_rMaxPhi_grid(YVAL, KAP, SIGMA, radians(THV))
                for c, R0 in enumerate(r0s):
                    G = R0
                    for PHI in phis:
                        RP = solveR(G, R0, PHI, KAP, SIGMA, THETA_V)
                        G = RP
                        # F = np.log10(np.power(np.divide(RP, R0), 2.0))
                        ps.append(PHI/np.pi)
                        rs.append(R0)
                        # fs.append(F)
                        fs.append(RP)
                        ks.append(KAP)
                        ts.append(THV)
                        cs.append(c)

        data = [ps, rs, ks, ts, fs, cs]
        df = pd.DataFrame(data)
        df = df.transpose()
        cols = ['Phi', 'R0P', 'Kappa', 'ThetaV', 'RP', 'C']
        df.columns = cols
        # df = df.round({'R0P': 3})
        # print df.groupby(['Kappa', 'ThetaV', 'C']).get_group((0.0, 1.0, 0.0))['RP']
        g = sns.FacetGrid(df, col='Kappa', row='ThetaV', hue='C',
                                xlim=(0,2),
                                palette = sns.color_palette("Spectral", n_colors=9)) #ylim=(0,2),
        g.map(plt.plot, "Phi", "RP", lw = 1)
        # g = sns.factorplot(x="Phi", y="FPhi", hue="C", row="ThetaV", col="Kappa",
                            # data=df, palette = sns.color_palette("Blues", n_colors=len(r0s)))
        g.set_axis_labels(r"$\phi [\pi]$", r"$Log[ f^2(\phi) ] = Log [ (r'/r_0')^2 ]$")
        for i in range(len(g.fig.get_axes())):
            handles, labels = g.fig.get_axes()[i].get_legend_handles_labels()
            thv_val = float(g.fig.get_axes()[i]
                            .get_title()
                            .split('|')[0]
                            .split('=')[1]
                            .strip()
                            )
            kap_val = float(g.fig.get_axes()[i]
                            .get_title()
                            .split('|')[1]
                            .split('=')[1]
                            .strip()
                            )
            # print kap_val, thv_val
            labs = ['{:.2e}'.format(df.groupby(['Kappa', 'ThetaV', 'C'])
                    .get_group((kap_val, thv_val, float(lab)))['R0P']
                    .unique()[0]) for lab in labels]
            g.fig.get_axes()[i].legend(handles, labs,
                                       loc='upper right',
                                       bbox_to_anchor=(1.2, 1.0))
        g.set_titles(r"$\kappa = {col_name}$ | $\theta_V = {row_name}$")
        plt.suptitle(r"$y={a} | r'_{{0,min}}={b}$".format(a=YVAL, b=TINY))
        g.fig.subplots_adjust(top=.9)
        plt.show()
        # plt.savefig("rPrime-phi_profiles(y={a}_r0'min={b}).pdf".format(a=YVAL, b=TINY), format="pdf", dpi=1200)


   # plot_r0Int_grid()
    # plot_r0Int_grid_cTest(0.9)
    # r0_integral()

    # # KAPPA = tiny
    # # for kap in range(10):
    # for kap in [0.0, 1.0, 3.0, 10.0]:
        # # KAPPA = np.power(10.0, -float(kap + 1))
        # KAPPA = float(kap)  # + 0.01
        # # print fluxG_fullStr(0.1, 0.5, 1.0, 2.0, radians(6.0))
        # str_int = nquad(fluxG_fullStr, [bounds_ry, bounds_yr],
                        # args = (KAPPA, SIGMA, THETA_V),
                        # opts = {'epsabs': 1.0e-5})
        # # str_int = quad(fluxG_fullStr, TINY, r0_max(YVAL, KAPPA, SIGMA, THETA_V) - TINY,
                        # # args = (YVAL, KAPPA, SIGMA, THETA_V), epsabs = 1.0e-5)
        # # str_int = romberg(vec_fluxG_fullStr, TINY, r0_max(YVAL, KAPPA, SIGMA, THETA_V) - TINY,
                            # # args = (YVAL, KAPPA, SIGMA, THETA_V), tol = 1.0e-5,
                            # # vec_func = True)
        # # str_int = quadrature(vec_fluxG_fullStr, TINY, r0_max(YVAL, KAPPA, SIGMA, THETA_V) - TINY,
                            # # args = (YVAL, KAPPA, SIGMA, THETA_V), tol = 1.0e-5,
                            # # vec_func = True)
        # print KAPPA, str_int

if __name__ == "__main__":
    # sys.exit(int(main(1.0e-9) or 0))
    # test_rmax()
    plot_root_grid()
