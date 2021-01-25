#--------------------------------------------------------------------------------------------------
# TREE OF CLASSES:
#     Reactor
#         Solid
#             FuelElement
#             Structure
#         Fluid
#         Neutron
#         Control
#             Detector
#             Controller
#--------------------------------------------------------------------------------------------------
from control import Control
from fluid import Fluid
from input import construct_input
from neutron import Neutron
from solid import Solid

# SciPy requires installation : 
#     python -m pip install --user numpy scipy matplotlib ipython jupyter pandas sympy nose
from scipy.integrate import ode

import json

#--------------------------------------------------------------------------------------------------
class Reactor:
    def __init__(self):
        self.input = construct_input()
        self.solid = Solid(self)
        self.fluid = Fluid(self)
        self.neutron = Neutron(self)
        self.control = Control(self)
        solve(self)
#--------------------------------------------------------------------------------------------------
def solve(reactor):

    def construct_rhs(t, y):
        rhs = []
        rhs += reactor.solid.calculate_rhs(reactor,t,y)
        rhs += reactor.fluid.calculate_rhs(reactor,t,y)
        rhs += reactor.neutron.calculate_rhs(reactor,t,y)
        rhs += reactor.control.calculate_rhs(reactor,t,y)
        return rhs

    solver = ode(construct_rhs, jac = None).set_integrator('lsoda', method = 'bdf')
    t0 = reactor.input['t0']
    y0 = [0, 0]
    solver.set_initial_value(y0, t0)
    dtout = reactor.input['dtout']
    tend = reactor.input['tend']
    while solver.successful() and solver.t < tend:
        time = solver.t + dtout
        y = solver.integrate(time)
        print(time, y)

#--------------------------------------------------------------------------------------------------
# create and solve
reactor = Reactor()