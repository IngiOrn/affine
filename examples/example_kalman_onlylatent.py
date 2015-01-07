import numpy as np
import numpy.ma as ma
import pandas as px
import datetime as dt

import socket
import atexit

from statsmodels.tsa.api import VAR
from statsmodels.tsa.filters.hp_filter import hpfilter
from statsmodels.sandbox.pca import Pca
from scipy import stats
from affine.model.affine import Affine
from affine.constructors.helper import (pickle_file, success_mail, to_mth,
                                        gen_guesses, ap_constructor, pass_ols)

#########################################
# Set up affine affine model            #
#########################################
# no observed factors
neqs = 0
latent = 3

#############################################
# Grab yield curve data                     #
#############################################

ycdata = px.read_csv("./data/yield_curve.csv", na_values = "M", sep=";",
                     index_col=0, parse_dates=True)

yc_cols = ['trcr_y1', 'trcr_y2', 'trcr_y3', 'trcr_y5', 'trcr_y7', 'trcr_y10']
mod_yc_data_nodp = ycdata[yc_cols]
mod_yc_data_nodp.rename(columns={'trcr_y1': 'trcr_q4', 'trcr_y2':
                                 'trcr_q8', 'trcr_y3': 'trcr_q12',
                                 'trcr_y5': 'trcr_q20', 'trcr_y7':
                                 'trcr_q28', 'trcr_y10': 'trcr_q40'},
                        inplace=True)
mod_yc_data = mod_yc_data_nodp.dropna(axis=0)

#limit to 1983 and on to not include Volker period
#dates = px.date_range("1/1/1983", "10/1/2009", freq="MS").to_pydatetime()
dates = px.date_range("6/1/1979", "12/1/2012", freq="MS").to_pydatetime()

mod_yc_data = mod_yc_data.ix[dates]

# Maturities
mats = [4, 8, 12, 20, 28, 40]

# construct model matrices up
lam_0_e = ma.zeros([latent, 1], dtype=np.complex_)
lam_1_e = ma.zeros([latent, latent], dtype=np.complex_)
delta_0_e = ma.zeros([1, 1], dtype=np.complex_)
delta_1_e = ma.zeros([latent, 1], dtype=np.complex_)
#delta_1_e[-latent:, 0] = [-0.0001, 0.0000, 0.0001]
#delta_1_e[-latent:, 0] = [0.0001]
mu_e = ma.zeros([latent, 1], dtype=np.complex_)
phi_e = ma.zeros([latent, latent], dtype=np.complex_)
sigma_e = ma.zeros([latent, latent], dtype=np.complex_)

#mask values to be estimated
lam_0_e[:, 0] = ma.masked
lam_1_e[:, :] = ma.masked
delta_0_e[:, :] = ma.masked
delta_1_e[-latent:, :] = ma.masked

mu_e[:, 0] = ma.masked
mu_e[:, 0] = ma.nomask

#assume phi lower triangular
#phi_e[:, :] = ma.masked
phi_e.mask = np.tri(phi_e.shape[0], M=phi_e.shape[1])

sigma_e[:, :] = ma.masked
sigma_e[:, :] = ma.nomask
sigma_e[:, :] = np.identity(latent)
#sigma_e[-latent:, -latent:] = ma.masked

mod_init = Affine(yc_data=mod_yc_data, var_data=None, latent=latent,
                  lam_0_e=lam_0_e, lam_1_e=lam_1_e, delta_0_e=delta_0_e,
                  delta_1_e=delta_1_e, mu_e=mu_e, phi_e=phi_e, sigma_e=sigma_e,
                  mats=mats, use_C_extension=False)

guess_length = mod_init.guess_length

guess_params = [0.0000] * guess_length

np.random.seed(100)

for numb, element in enumerate(guess_params):
    element = 0.01
    guess_params[numb] = np.abs(element * np.random.random())

bsr_solve = mod_init.solve(guess_params=guess_params, method="kalman",
                           alg="bfgs", maxfev=10000000, maxiter=10000000)
