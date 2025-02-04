""" 
Implemenentation for the resource scheduling problem 
for Research 
"""

from pulp import *
import numpy as np

parameters = np.genfromtxt("parameters.csv",delimiter=',',dtype=None)
resources = np.genfromtxt("resources.csv",delimiter=',',dtype=None)
constMax = np.genfromtxt("constMax.csv",delimiter=',',dtype=None)
constMin = np.genfromtxt("constMin.csv",delimiter=',',dtype=None)

print(parameters)
print(resources)
print(constMax)
print(constMin)




problem = LpProblem("Resource Scheduling FTE", LpMaximize)

nrOfProjects = parameters.size
nrOfResoources = resources.size 
nrOfVariables = nrOfProjects * nrOfResoources
variables = []

index = 0
for i in range(nrOfProjects):
    for j in range(nrOfResoources):
        #print(str(parameters[i][0]))
        #print(str(resources[j][0]))  
        variables.append( LpVariable(str(parameters[i][0])+str(resources[j][0]), 0, None, LpContinuous))
        print(variables[index])
        index += 1


#problem.writeLP("ResourceScheduling.lp")
#problem.solve()
#for v in problem.variables():
#    print(v.name, "=", v.varValue)