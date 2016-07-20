'''
An example of the lake problem using the ema workbench. 

The model itself is adapted from the Rhodium example by Dave Hadka,
see https://gist.github.com/dhadka/a8d7095c98130d8f73bc

'''
from __future__ import (unicode_literals, print_function, absolute_import,
                        division)

import math

import numpy as np
from scipy.optimize import brentq as root

from ema_workbench.em_framework import (ModelEnsemble, ModelStructureInterface, 
                                        RealParameter, ScalarOutcome)
from ema_workbench.util import ema_logging
from ema_workbench.em_framework.parameters import Constant

def lake_problem(decisions=[],
         b = 0.42,          # decay rate for P in lake (0.42 = irreversible)
         q = 2.0,           # recycling exponent
         mean = 0.02,       # mean of natural inflows
         stdev = 0.001,     # future utility discount rate
         delta = 0.98,      # standard deviation of natural inflows
         alpha = 0.4,       # utility from pollution
         nsamples = 100):   # Monte Carlo sampling of natural inflows
                
    Pcrit = root(lambda x: x**q/(1+x**q) - b*x, 0.01, 1.5)
    nvars = len(decisions)
    X = np.zeros((nvars,))
    average_daily_P = np.zeros((nvars,))
    decisions = np.array(decisions)
    reliability = 0.0

    for _ in xrange(nsamples):
        X[0] = 0.0
        
        natural_inflows = np.random.lognormal(
                math.log(mean**2 / math.sqrt(stdev**2 + mean**2)),
                math.sqrt(math.log(1.0 + stdev**2 / mean**2)),
                size = nvars)
        
        for t in xrange(1,nvars):
            X[t] = (1-b)*X[t-1] + X[t-1]**q/(1+X[t-1]**q) + decisions[t-1] + natural_inflows[t-1]
            average_daily_P[t] += X[t]/float(nsamples)
    
        reliability += np.sum(X < Pcrit)/float(nsamples*nvars)
      
    max_P = np.max(average_daily_P)
    utility = np.sum(alpha*decisions*np.power(delta,np.arange(nvars)))
    inertia = np.sum(np.diff(decisions) > -0.02)/float(nvars-1)
    
    return {'max_P':max_P, 'utility':utility, 
            'inertia':inertia, 'reliability':reliability}

if __name__ == '__main__':
    ema_logging.log_to_stderr(ema_logging.INFO)
    
    #instantiate the model
    model = ModelStructureInterface('lakeproblem', function=lake_problem)

    #specify uncertainties
    model.uncertainties = [RealParameter("b", 0.1, 0.45),
                           RealParameter("q", 2.0, 4.5),
                           RealParameter("mean", 0.01, 0.05),
                           RealParameter("stdev", 0.001, 0.005),
                           RealParameter("delta", 0.93, 0.99)]
    #specify outcomes 
    model.outcomes = [ScalarOutcome("max_P",),
                      ScalarOutcome("utility"),
                      ScalarOutcome("inertia"),
                      ScalarOutcome("reliability")]
    
    # override some of the defaults of the model
    model.constants = [Constant('alpha', 0.41),
                       Constant('nsamples', 150),]

    ensemble = ModelEnsemble() #instantiate an ensemble
    ensemble.model_structure = model #set the model on the ensemble
    ensemble.parallel = True
    ensemble.policies = [ {'name':'0.01', 
                           'decisions' : [0.01,]*100} ]
    
    #run 1000 experiments
    results = ensemble.perform_experiments(150, reporting_interval=10) 