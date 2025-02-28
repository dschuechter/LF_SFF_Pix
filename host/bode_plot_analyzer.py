# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
# 
# This script is designed to work with the LF SFF Test Board. For different boards you probably would
# need to change the threshold values, limits,...
# Generally the analyse_bode_plot(...) function expect the y values in dB -> Thresholds
#

import numpy as np
import matplotlib.pyplot as plt
from scipy import optimize
import utils.plot_fit as pltfit
import time

# fit function for the rising and falling edges
def lin_fit(x,a,b):
    return a*x+b

# fit function for the plateau
def const_fit(x,a):
    return x*0+a

def analyse_bode_plot(x,y,xerr,yerr, title, chip_version, DC_offset, output_path=None, IBN=None, IBP=None, show_plot = False):
    dc_gain = 1
    dc_gain_err = 0.00001

    if IBN:
        try:
            dc_gain = np.genfromtxt('./output/DC_sweeps/'+chip_version+'/data/IBN_'+str(IBN)+'_Gain.csv', delimiter=',')
            dc_gain_select = np.argmin(np.abs(dc_gain[1:,0]-DC_offset))
            dc_gain_err = dc_gain[dc_gain_select][3]
            dc_gain = dc_gain[dc_gain_select][2]
        except:
            print('Could not load DC Gain for bodeplot. Applying defaults: G=(1+-0.00001)')

    if IBP:
        try:
            dc_gain = np.genfromtxt('./output/DC_sweeps/'+chip_version+'/data/IBP_'+str(IBP)+'_Gain.csv', delimiter=',')
            dc_gain_select = np.argmin(np.abs(dc_gain[1:,0]-DC_offset))
            dc_gain_err = dc_gain[dc_gain_select][3]
            dc_gain = dc_gain[dc_gain_select][2]
        except:
            print('Could not load DC Gain for bodeplot. Applying defaults: G=(1+-0.00001)')
            
    
    f_hp, f_hp_err,f_tp, f_tp_err, C_in = None,None,None,None,None  
    if chip_version == 'AC':  
        y = 10*np.log10(np.abs(y)/dc_gain)
        yerr = np.sqrt((np.abs(10/(y*np.log10(10)))*yerr)**2+(10/(dc_gain*np.log(10))*dc_gain_err)**2)
    else:
        y = 10*np.log10(np.abs(y))
        yerr = np.sqrt((np.abs(10/(y*np.log10(10)))*yerr)**2+(10/(dc_gain*np.log(10))*dc_gain_err)**2)
    #yerr = np.abs(10*np.log10(np.abs(yerr)))
    x = np.array(x)
    xerr = np.array(xerr)
    yerr = np.array(yerr)
    pltfit.beauty_plot(log_x=True,xlabel='f / Hz', ylabel='$V_{pp}(LF SFF)/V_{pp}(IN)$ in dB', title=title, ylim=[np.min(y)-3,np.max(y)+3], xlim=[1,1.5*1e7])
    plt.errorbar(x=x,y=y,xerr=xerr,yerr=yerr, linestyle='None', marker='.')
    ###### find pleateau
    plateau_max = np.max(y)
    threshold = 0.7

    plateau = [i for i in range(0, len(y)) if y[i]>plateau_max-threshold]
    plt.fill_between([x[plateau[0]],x[plateau[-1]]], -1000,1000, alpha=0.2, color='gray')   

    popt_plateau, perr_plateau =  optimize.curve_fit(const_fit, x[plateau],y[plateau],[plateau_max])
    Gain = 10**(popt_plateau[0]/10)
    Gain_err = 10**(popt_plateau[0]/10-1)*np.log10(10)
    plt.text(1e4, np.min(y)+1, '$G_{AC sweep}=(%.3f\\pm%.3f)$'%(Gain, Gain_err))
    plt.text(1e4, np.min(y), '$G_{DC sweep}=(%.3f\\pm%.3f)$'%(dc_gain, dc_gain_err))
    C_in = 0
    C_in_err = 0
    if chip_version != 'DC':
        C_ac = 6*1e-15
        C_in = (C_ac*(1/Gain-1))*1e15
        C_in_err = C_ac/Gain**2*Gain_err*1e15
        plt.text(1e4, np.min(y)-1, '$C_{in}=(%.3f\\pm%.3f)$fF'%(C_in, C_in_err))
    x_fit_plateau = np.linspace(0, 1e9, 2)
    plt.plot(x_fit_plateau,const_fit(x_fit_plateau,popt_plateau), color='black', label='plateau')
    plt.hlines(plateau_max-threshold, 0,10**9, linestyle='-.', colors='black', label='plateau threshold')
    ###### find rising/falling region
    left = []
    for i in range(0, len(y)):
        if y[i] not in y[plateau]:
            left.append(i)
        else:
            break
    minus3dB = popt_plateau-3
    minus3dB_err = perr_plateau
    plt.hlines(minus3dB,0,10**9, linestyle='dotted', colors='black', label='plateau-3dB')

    right = [i for i in range(np.max(plateau), len(y))]
    ###### fit linear functions to sides
    skip_first_n_values_left = 10
    fit_first_n_values_right = len(right)-6
    if len(left)>=6:
        plt.scatter(x=x[left][skip_first_n_values_left:], y=y[left][skip_first_n_values_left:])
        popt_left, perr_left = pltfit.double_err(function=pltfit.func_lin, x=np.log10(x[left][skip_first_n_values_left:]),x_error=np.log10(xerr[left][skip_first_n_values_left:]), y=y[left][skip_first_n_values_left:], y_error=yerr[left][skip_first_n_values_left:], presets=[1,1])
        plt.plot([1,1e12], pltfit.func_lin(x=np.log10([1,1e12]), p=popt_left))
        f_hp =  10**((minus3dB-popt_left[1])/popt_left[0])
        f_hp_err = np.sqrt(2*(np.log(10)*10**((minus3dB-popt_left[1])/popt_left[0])/popt_left[0]*perr_left[1])**2+(np.log(10)*(minus3dB-popt_left[1])*10**((minus3dB-popt_left[1])/popt_left[0])/popt_left[0]**2*perr_left[0])**2)
    if len(right)>=3:
        popt_right, perr_right = pltfit.double_err(function=pltfit.func_lin, x=np.log10(x[right][-fit_first_n_values_right:]),x_error=np.log10(xerr[right][-fit_first_n_values_right::]), y=y[right][-fit_first_n_values_right::], y_error=yerr[right][-fit_first_n_values_right::], presets=[1,1])
        plt.plot([1,1e12], pltfit.func_lin(x=np.log10([1,1e12]), p=popt_right))
        f_tp =  10**((minus3dB-popt_right[1])/popt_right[0])
        f_tp_err = np.sqrt(2*(np.log(10)*10**((minus3dB-popt_right[1])/popt_right[0])/popt_right[0]*perr_right[1])**2+(np.log(10)*(minus3dB-popt_right[1])*10**((minus3dB-popt_right[1])/popt_right[0])/popt_right[0]**2*perr_right[0])**2)
    try:
        plt.vlines(f_tp,10,-100, linestyles='--', color='black', label='$f_{tp}=(%.3f\\pm%.3f)$MHz'%(f_tp*1e-6, f_tp_err*1e-6))
    except:
        print('Could not find f_tp')
    R_off = 0
    R_off_err = 0
    try:
        R_off = 2*np.pi/(C_ac*f_hp)
        R_off_err = 2*np.pi/(C_ac*f_hp**2)*f_hp_err
        plt.text(1e4, np.min(y)-2, '$R_{off}=(%.4f\\pm%.4f)$M$\Omega$'%(R_off*1e-6, R_off_err*1e-6))

        plt.vlines(f_hp,10,-100, linestyles='--', color='black', label='$f_{hp}=(%.3f\\pm%.3f)$Hz'%(f_hp, f_hp_err))        
    except:
        print('Could not find f_hp')
    plt.legend()
    if output_path:
        plt.savefig(output_path)
    if show_plot:
        plt.show()
    plt.close()
    return Gain, Gain_err, f_tp, f_tp_err, f_hp, f_hp_err, C_in, C_in_err, R_off, R_off_err

#data=np.genfromtxt("bode.csv", delimiter=',')
#y = data[0:,1]
#x = data[0:,0]
#yerr = [1 for i in range(0, len(y))]
#xerr = [1 for i in range(0, len(x))]
#analyse_bode_plot(x,y,xerr,yerr,'kjansdbh')