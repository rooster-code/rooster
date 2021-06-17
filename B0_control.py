from scipy.interpolate import interp1d

import datetime
import json
import os
import shutil
import sys

#--------------------------------------------------------------------------------------------------
class Control:

    # constructor: self is a 'control' object created in B
    def __init__(self, reactor):
        self.input = self.construct_input()

    #------------------------------------------------------------------------------------------
    def evaluate_signals(self, reactor, t):

        # evaluate signals
        self.signal = {}
        for s in self.input['signal']:
            if type(s['value']) == int or type(s['value']) == float:
                self.signal[s['id']] = s['value']
            if s['value'] == 'time':
                self.signal[s['id']] = t

        #evaluate output signals of lookup tables
        lookup_table = self.input['lookup']
        for table in lookup_table:
            insignal_name = table['x'][0]
            outsignal_name = table['f(x)'][0]
            x = table['x'][1:]
            y = table['f(x)'][1:]
            # scipy function
            f = interp1d(x, y)
            xnew = max(min(self.signal[insignal_name],x[-1]),x[0])
            ynew = f(xnew)
            self.signal[outsignal_name] = ynew

        # signal-dependent junction: impose flowrate
        if 'fluid' in reactor.solve:
            for j in range(reactor.fluid.njun):
                if reactor.fluid.juntype[j] == 'independent' and reactor.fluid.junflowrate[j] != '':
                    # impose flowrate from the look-up table
                    reactor.fluid.mdoti[j] = self.signal[reactor.fluid.junflowrate[j]]
        
        # signal-dependent pipe: impose temperature
        if 'fluid' in reactor.solve:
            for i in range(reactor.fluid.npipe):
                if reactor.fluid.pipetype[i] == 'normal' and reactor.fluid.signaltemp[i] != '':
                    # impose temperature from the look-up table
                    reactor.fluid.temp[i] = [self.signal[reactor.fluid.signaltemp[i]]] * reactor.fluid.pipennodes[i]


    #----------------------------------------------------------------------------------------------
    def construct_input(self):
        #create dictionary inp where all input data will be stored
        inp = {}
        inp['clad'] = []
        inp['coregeom'] = {'geometry':'', 'pitch':0, 'botBC':'', 'topBC':''}
        inp['coremap'] = []
        inp['fuel'] = []
        inp['fuelrod'] = []
        inp['innergas'] = []
        inp['junction'] = {'from':[], 'to':[], 'type':[], 'pumphead':[], 'flowrate':[]}
        inp['lookup'] = []
        inp['mat'] = []
        inp['mix'] = []
        inp['p2d'] = []
        inp['pipe'] = []
        inp['signal'] = []
        inp['signalid'] = []
        inp['solve'] = []
        inp['stack'] = []
        inp['t0'] = 0
        inp['t_dt'] = []
    
        #read input file as a whole
        f = open('input', 'r')
        s0 = f.read()
        f.close()
    
        #merge &-ending "line" with the next one
        s = ''
        take = True
        for c in s0:
            if c == '&' : take = False
            if take : s += c
            if c == '\n' : take = True
    
        #split in lines
        lines = s.strip().split('\n')
    
        #remove comment-lines (*)
        lines = [x for x in lines if not x.startswith('*')]
        #remove comments inside lines (*)
        for i in range(len(lines)):
            if '*' in lines[i]:
                lines[i] = lines[i].split('*')[0]
    
        def convert_to_float(w): 
            try:
                w = float(w)
            except:
                pass
            return w

        for line in lines:
                
            word = line.split()
            word = list(map(convert_to_float, word))
            if len(word) > 0:
                
                key = word[0].lower()
                #--------------------------------------------------------------------------------------
                # just placeholder
                if key == '':
                    pass
                #--------------------------------------------------------------------------------------
                # effective delayed neutron fractions
                elif key == 'betaeff':
                    inp['betaeff'] = word[1:]
                #--------------------------------------------------------------------------------------
                # cladding
                elif key == 'clad':
                     inp['clad'].append( {'id':word[1], 'matid':word[2], 'ri':word[3], 'ro':word[4], 'nr':int(word[5])} )
                #--------------------------------------------------------------------------------------
                # core geometry
                elif key == 'coregeom':
                    if len(word)-1 < 4:
                        print('****ERROR: coregeom card should have four values after the keyword: geometry flag (hex01, hex06, hex24, square), pitch (distance between node centres), bottom boundary conditions (0: vacuum, -1: reflective), top boundary conditions (0: vacuum, -1: reflective).')
                        sys.exit()
                    list_of_geometries = ['square','hex01', 'hex06', 'hex24']
                    if not word[1] in list_of_geometries:
                        print('****ERROR: geometry flag of coregeom card (word 2) is wrong: ', word[1], '\nCorrect values are: ')
                        for v in list_of_geometries:
                            print(v)
                        sys.exit()
                    if not isinstance(word[2],int) and not isinstance(word[2],float):
                        print('****ERROR: node pitch (m) of coregeom card (word 3) is not numeric: ', word[2])
                        sys.exit()
                    if word[3] != 0 and word[3] != 1:
                        print('****ERROR: bottom boundary condition flag of coregeom card (word 4) is wrong: ', word[3], '\nCorrect values are:\n0 (vacuum)\n1 (reflective)')
                        sys.exit()
                    if word[4] != 0 and word[4] != 1:
                        print('****ERROR: top boundary condition flag of coregeom card (word 5) is wrong: ', word[4], '\nCorrect values are:\n0 (vacuum)\n1 (reflective)')
                        sys.exit()
                    inp['coregeom'] = {'geom':word[1], 'pitch':word[2], 'botBC':int(word[3]), 'topBC':int(word[4])}
                #--------------------------------------------------------------------------------------
                # core map
                elif key == 'coremap':
                    inp['coremap'].append(word[1:])
                #--------------------------------------------------------------------------------------
                # delayed neutron precursor decay time constants
                elif key == 'dnplmb':
                    inp['dnplmb'] = word[1:]
                #--------------------------------------------------------------------------------------
                # fuel grain parameters
                elif key == 'fgrain':
                    # grain diameter
                    inp['dgrain'] = word[1]
                    # number of nodes in the grain
                    inp['nrgrain'] = int(word[2])
                    # fission rate
                    inp['frate'] = int(word[3])
                #--------------------------------------------------------------------------------------
                # fuel
                elif key == 'fuel':
                     inp['fuel'].append( {'id':word[1], 'matid':word[2], 'ri':word[3], 'ro':word[4], 'nr':int(word[5])} )
                #--------------------------------------------------------------------------------------
                # fuel rod card
                elif key == 'fuelrod':
                    id = word[1]
                    if any([id in x['id'] for x in inp['fuelrod']]):
                        for x in inp['fuelrod']:
                            if x['id'] == id:
                                x['fuelid'].append(word[2])
                                x['hgap'].append(float(word[3]))
                                x['cladid'].append(word[4])
                                x['p2d'].append(word[5])
                                x['mltpl'].append(word[6])
                                x['pipeid'].append(word[7])
                                x['pipenode'].append(int(word[8]))
                    else:
                        inp['fuelrod'].append({'id':id, 'fuelid':[word[2]], 'hgap':[float(word[3])], 'cladid':[word[4]], 'p2d':[word[5]], 'mltpl':[word[6]], 'pipeid':[word[7]], 'pipenode':[int(word[8])]})
                #--------------------------------------------------------------------------------------
                # inner gas
                elif key == 'innergas':
                     inp['innergas'].append( {'fuelrodid':word[1], 'matid':word[2], 'plenv':word[3]} )
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic junction (dependent)
                elif key == 'jun':
                     inp['junction']['from'].append(word[1])
                     inp['junction']['to'].append(word[2])
                     inp['junction']['type'].append('dependent')
                     inp['junction']['pumphead'].append('')
                     inp['junction']['flowrate'].append('')
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic junction (independent)
                elif key == 'jun-i':
                     inp['junction']['from'].append(word[1])
                     inp['junction']['to'].append(word[2])
                     inp['junction']['type'].append('independent')
                     inp['junction']['pumphead'].append('')
                     inp['junction']['flowrate'].append('')
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic junction (independent + signal for flowrate)
                elif key == 'jun-i-f':
                     inp['junction']['from'].append(word[1])
                     inp['junction']['to'].append(word[2])
                     inp['junction']['type'].append('independent')
                     inp['junction']['pumphead'].append('')
                     inp['junction']['flowrate'].append(word[3])
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic junction (independent + signal for pump head)
                elif key == 'jun-i-p':
                     inp['junction']['from'].append(word[1])
                     inp['junction']['to'].append(word[2])
                     inp['junction']['type'].append('independent')
                     inp['junction']['pumphead'].append(word[3])
                     inp['junction']['flowrate'].append('')
                #--------------------------------------------------------------------------------------
                # lookup table
                elif key == 'lookup':
                     lookup = {}
                     lookup['x'] = word[1::2]
                     lookup['f(x)'] = word[2::2]
                     inp['lookup'].append(lookup)
                #--------------------------------------------------------------------------------------
                # material
                elif key == 'mat':
                     if word[2] == 'he':
                         inp['mat'].append( {'id':word[1], 'type':word[2], 'p0':word[3], 'temp0':word[4]} )
                     elif word[2] == 'mox':
                         inp['mat'].append( {'id':word[1], 'type':word[2], 'pu':word[3], 'b':word[4], 'x':word[5], 'por':word[6], 'temp0':word[7]} )
                     elif word[2] == 'na':
                         inp['mat'].append( {'id':word[1], 'type':word[2], 'p0':word[3], 'temp0':word[4]} )
                     elif word[2] == 'ss316':
                         inp['mat'].append( {'id':word[1], 'type':word[2], 'temp0':word[3]} )
                #--------------------------------------------------------------------------------------
                # mixture of isotopes
                elif key == 'mix':
                    if len(word)-1 < 4:
                        print('****ERROR: mix card should have four values after the keyword: mix id, isotopeid, number density and signal id for temperature.')
                        sys.exit()
                    
                    mixid = word[1]
                    if any([mixid in x['mixid'] for x in inp['mix']]):
                        for x in inp['mix']:
                            if x['mixid'] == mixid:
                                x['isoid'].append(word[2])
                                x['numdens'].append(float(word[3]))
                                x['signaltemp'].append(word[4])
                    else:
                        inp['mix'].append({'mixid':mixid, 'isoid':[word[2]], 'numdens':[float(word[3])], 'signaltemp':[word[4]]})
                #--------------------------------------------------------------------------------------
                # nuclear data directory
                elif key == 'nddir':
                     inp['nddir'] = word[1]
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic pipe without free level
                elif key == 'pipe':
                     inp['pipe'].append( {'id':word[1], 'type':'normal', 'matid':word[2], 'dhyd':word[3], 'len':word[4], 'dir':word[5], 'areaz':word[6], 'nnodes':int(word[7]), 'signaltemp':''} )
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic pipe with free level
                elif key == 'pipe-f':
                     inp['pipe'].append( {'id':word[1], 'type':'freelevel', 'matid':word[2], 'dhyd':word[3], 'len':word[4], 'dir':word[5], 'areaz':word[6], 'nnodes':1, 'signaltemp':''} )
                #--------------------------------------------------------------------------------------
                # thermal-hydraulic pipe without free level with temperature defined by signal
                elif key == 'pipe-t':
                     inp['pipe'].append( {'id':word[1], 'type':'normal', 'matid':word[2], 'dhyd':word[3], 'len':word[4], 'dir':word[5], 'areaz':word[6], 'nnodes':int(word[7]), 'signaltemp':word[8]} )
                #--------------------------------------------------------------------------------------
                # initial reactor power
                elif key == 'power0':
                     inp['power0'] = float(word[1])
                #--------------------------------------------------------------------------------------
                # signal variable
                elif key == 'signal':
                     signal = {}
                     signal['id'] = word[1]
                     if len(word[2:]) == 1:
                         signal['value'] = word[2]
                     else:
                         signal['symexp'] = word[2:]
                     inp['signal'].append(signal)
                #--------------------------------------------------------------------------------------
                # models to be solved
                elif key == 'solve':
                    inp['solve'].append(word[1])
                    # verify that solve card has correct value
                    correct_values = {'fluid','fuelgrain','fuelrod','pointkinetics','spatialkinetics'}
                    value = set([word[1]])
                    diff = value.difference(correct_values)
                    if diff != set():
                        print('****ERROR: solve card contains wrong value: ', list(diff)[0], '\nCorrect values are: ')
                        sorted = list(correct_values)
                        sorted.sort()
                        for v in sorted:
                            print('solve', v)
                        sys.exit()
                    if word[1] == 'spatialkinetics':
                        # check that there is a second value
                        if len(word)-1 == 1:
                            print('****ERROR: solve spatialkinetics card should have a second value after the keyword: number of energy groups (integer), e.g.:\nsolve spatialkinetics 25')
                            sys.exit()
                        # check that there the second value is integer
                        try:
                            # number of energy groups
                            inp['ng'] = int(word[2])
                        except:
                            print('****ERROR: the second value after the keyword of solve spatialkinetics card should be integer (number of energy groups), e.g.:\nsolve spatialkinetics 25')
                            sys.exit()
                #--------------------------------------------------------------------------------------
                # stack of mixes of isotopes
                elif key == 'stack':
                    if len(word)-1 < 4:
                        print('****ERROR: stack card should have four values after the keyword: stack id, mix id, pipe id, pipe node.')
                        sys.exit()
                    
                    stackid = word[1]
                    if any([stackid in x['stackid'] for x in inp['stack']]):
                        for x in inp['stack']:
                            if x['stackid'] == stackid:
                                x['mixid'].append(word[2])
                                x['pipeid'].append(word[3])
                                x['pipenode'].append(int(word[4]))
                    else:
                        inp['stack'].append({'stackid':stackid, 'mixid':[word[2]], 'pipeid':[word[3]], 'pipenode':[int(word[4])]})
                #--------------------------------------------------------------------------------------
                # integration starting time
                elif key == 't0':
                    inp['t0'] = word[1]
                #--------------------------------------------------------------------------------------
                # end of time interval and output time step for this interval
                elif key == 't_dt':
                    inp['t_dt'].append([word[1], word[2]])
                #--------------------------------------------------------------------------------------
                # prompt neutron lifetime
                elif key == 'tlife':
                    inp['tlife'] = word[1]
    
        # verify that t_dt present
        if inp['t_dt'] == []:
            sys.exit('****ERROR: obligatory card t_dt specifying time_end and dtime_out is absent.')
            sys.exit()
    
        # verify that there is at least one solve card
        if len(inp['solve']) == 0:
            print('****ERROR: input file should have at least one solve card.')
            sys.exit()
        if 'fuelgrain' in inp['solve'] and 'fuelrod' not in inp['solve']:
            print('****ERROR: \'solve fuelgrain\' card requires \'solve fuelrod\' card.')
            sys.exit()
    
        # make a list of all signals
        inp['signalid'] = [x['id'] for x in inp['signal']]
        # verify that lookup tables use existing signals
        for table in inp['lookup']:
            insignal = table['x'][0]
            outsignal = table['f(x)'][0]
            if insignal not in inp['signalid']:
                print('****ERROR: input signal ' + insignal + ' in lookup table ' + outsignal + ' is not defined.')
                sys.exit()
        # append output signals of lookup tables
        inp['signalid'] += [y['f(x)'][0] for y in inp['lookup']]
    
        # verify that mix card uses existing signals
        for s in [x['signaltemp'][j] for x in inp['mix'] for j in range(len(x['signaltemp']))]:
            if s not in inp['signalid']:
                print('****ERROR: signal for temperature ' + s + ' in mix card is not defined.')
                sys.exit()
    
        fid = open('input.json', 'w')
        fid.write(json.dumps(inp, indent=2))
        fid.close()
        return inp

    #----------------------------------------------------------------------------------------------
    def open_output_files(self, reactor):

        # prepare an output folder
        path4results = 'output'
        if os.path.isfile(path4results): os.remove(path4results)
        if not os.path.isdir(path4results): os.mkdir(path4results)
        path4results += os.sep + str(datetime.datetime.now())[0:21].replace(' ','-').replace(':','-').replace('.','-')
        if os.path.isfile(path4results): os.remove(path4results)
        if not os.path.isdir(path4results): os.mkdir(path4results)

        # copy input files to output folder
        shutil.copyfile('input', path4results + os.sep + 'input')
        shutil.copyfile('input.json', path4results + os.sep + 'input.json')
        # open files for output
        fid = []
        if 'fuelrod' in reactor.solve:
            for i in range(reactor.solid.nfuelrods):
                fid.append(open(path4results + os.sep + 'fuelrod-hgap-' + [x['id'] for x in self.input['fuelrod']][i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('hgap-' + str(j).zfill(3)).ljust(13) for j in range(reactor.solid.fuelrod[i].nz)]) + '\n')
                for j in range(reactor.solid.fuelrod[i].nz):
                    fid.append(open(path4results + os.sep + 'fuelrod-temp-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '.dat', 'w'))
                    fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('tempf-' + str(k).zfill(3) + '(K)').ljust(13) for k in range(reactor.solid.fuelrod[i].fuel[j].nr)]) + ''.join([('tempc-' + str(k).zfill(3) + '(K)').ljust(13) for k in range(reactor.solid.fuelrod[i].clad[j].nr)]) + '\n')
                    for k in range(reactor.solid.fuelrod[i].fuel[j].nr):
                        if 'fuelgrain' in reactor.solve and i + j + k == 0: 
                            fid.append(open(path4results + os.sep + 'fuelrod-c1-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '-' + str(k).zfill(3) + '.dat', 'w'))
                            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('c1-' + str(l).zfill(3)).ljust(13) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].nr)]) + '\n')
                            fid.append(open(path4results + os.sep + 'fuelrod-ri-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '-' + str(k).zfill(3) + '.dat', 'w'))
                            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('ri-' + str(l).zfill(3)).ljust(13) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            fid.append(open(path4results + os.sep + 'fuelrod-cv_irr-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '-' + str(k).zfill(3) + '.dat', 'w'))
                            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('cv_irr-' + str(l).zfill(3)).ljust(13) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            fid.append(open(path4results + os.sep + 'fuelrod-ci_irr-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '-' + str(k).zfill(3) + '.dat', 'w'))
                            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('ci_irr-' + str(l).zfill(3)).ljust(13) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            fid.append(open(path4results + os.sep + 'fuelrod-cv_p-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '-' + str(k).zfill(3) + '.dat', 'w'))
                            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('cv_p-' + str(l).zfill(3)).ljust(13) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            fid.append(open(path4results + os.sep + 'fuelrod-bi-' + [x['id'] for x in self.input['fuelrod']][i] + '-' + str(j).zfill(3) + '-' + str(k).zfill(3) + '.dat', 'w'))
                            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('bi-' + str(l).zfill(3)).ljust(13) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
        if 'fluid' in reactor.solve:
            fid.append(open(path4results + os.sep + 'fluid-mdot.dat', 'w'))
            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([(self.input['junction']['from'][j] +'-' + self.input['junction']['to'][j]).ljust(13) for j in range(reactor.fluid.njuni + reactor.fluid.njund)]) + '\n')
            for i in range(reactor.fluid.npipe):
                fid.append(open(path4results + os.sep + 'fluid-p-' + reactor.fluid.pipeid[i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([str(j).zfill(4).ljust(13) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                fid.append(open(path4results + os.sep + 'fluid-temp-' + reactor.fluid.pipeid[i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([str(j).zfill(4).ljust(13) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                fid.append(open(path4results + os.sep + 'fluid-vel-' + reactor.fluid.pipeid[i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([str(j).zfill(4).ljust(13) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                fid.append(open(path4results + os.sep + 'fluid-re-' + reactor.fluid.pipeid[i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([str(j).zfill(4).ljust(13) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                fid.append(open(path4results + os.sep + 'fluid-pr-' + reactor.fluid.pipeid[i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([str(j).zfill(4).ljust(13) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                fid.append(open(path4results + os.sep + 'fluid-pe-' + reactor.fluid.pipeid[i] + '.dat', 'w'))
                fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([str(j).zfill(4).ljust(13) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
        if 'pointkinetics' in reactor.solve:
            fid.append(open(path4results + os.sep + 'core-power.dat', 'w'))
            fid[-1].write(' ' + 'time(s)'.ljust(13) + 'power(-)\n')
            fid.append(open(path4results + os.sep + 'core-cdnp.dat', 'w'))
            fid[-1].write(' ' + 'time(s)'.ljust(13) + ''.join([('cdnp-' + str(i)).ljust(13) for i in range(reactor.core.ndnp)]) + '\n')
        if 'spatialkinetics' in reactor.solve:
            for i in range(reactor.core.niso):
                fid.append(open(path4results + os.sep + 'core-iso-microxs-' + reactor.core.isoname[i] + '.dat', 'w'))
            for i in range(reactor.core.nmix):
                fid.append(open(path4results + os.sep + 'core-mix-macroxs-' + reactor.core.mix[i].mixid + '.dat', 'w'))
            fid.append(open(path4results + os.sep + 'core-k.dat', 'w'))
            fid[-1].write(' ' + 'niter'.ljust(13) + 'k'.ljust(13) + '\n')
            fid.append(open(path4results + os.sep + 'core-flux.dat', 'w'))
            fid[-1].write(' ' + 'time(s)'.ljust(13) + 'igroup'.ljust(13) + 'iz'.ljust(13) + 'iy'.ljust(13) + 'ix'.ljust(13) + 'flux'.ljust(13) + '\n')
            fid.append(open(path4results + os.sep + 'core-pow.dat', 'w'))
            fid[-1].write(' ' + 'time(s)'.ljust(13) + 'iz'.ljust(13) + 'iy'.ljust(13) + 'ix'.ljust(13) + 'pow'.ljust(13) + '\n')
            fid.append(open(path4results + os.sep + 'core-powxy.dat', 'w'))
            fid[-1].write(' ' + 'time(s)'.ljust(13) + 'iy'.ljust(13) + 'ix'.ljust(13) + 'pow'.ljust(13) + '\n')
        return fid

    #----------------------------------------------------------------------------------------------
    def print_output_files(self, reactor, fid, time, flag):

        # print output files
        indx = 0
        if 'fuelrod' in reactor.solve:
            for i in range(reactor.solid.nfuelrods):
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].innergas.hgap[j]) for j in range(reactor.solid.fuelrod[i].nz)]) + '\n')
                indx += 1
                # fuel and clad temperatures
                for j in range(reactor.solid.fuelrod[i].nz):
                    fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].temp[k]) for k in range(reactor.solid.fuelrod[i].fuel[j].nr)]) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].clad[j].temp[k]) for k in range(reactor.solid.fuelrod[i].clad[j].nr)]) + '\n')
                    indx += 1
                    for k in range(reactor.solid.fuelrod[i].fuel[j].nr):
                        if 'fuelgrain' in reactor.solve and i + j + k == 0: 
                            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].c1[l]) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].nr)]) + '\n')
                            indx += 1
                            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].ri[l]) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            indx += 1
                            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].cv_irr[l]) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            indx += 1
                            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].ci_irr[l]) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            indx += 1
                            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].cv_p[l]) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            indx += 1
                            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].bi[l]) for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB)]) + '\n')
                            indx += 1
        if 'fluid' in reactor.solve:
            # flowrate in dependent and independent junctions (no internal junctions)
            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.mdot[i]) for i in range(reactor.fluid.njuni + reactor.fluid.njund)]) + '\n')
            indx += 1
            for i in range(reactor.fluid.npipe):
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.p[i][j]) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                indx += 1
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.temp[i][j]) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                indx += 1
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.vel[i][j]) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                indx += 1
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.re[i][j]) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                indx += 1
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.pr[i][j]) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                indx += 1
                fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.fluid.pe[i][j]) for j in range(reactor.fluid.pipennodes[i])]) + '\n')
                indx += 1
        if 'pointkinetics' in reactor.solve:
            # point kinetics power
            fid[indx].write('{0:12.5e} '.format(time) + '{0:12.5e} '.format(reactor.core.power) + '\n')
            indx += 1
            # point kinetics cdnp
            fid[indx].write('{0:12.5e} '.format(time) + ''.join(['{0:12.5e} '.format(reactor.core.cdnp[i]) for i in range(reactor.core.ndnp)]) + '\n')
            indx += 1
        if 'spatialkinetics' in reactor.solve:
            for i in range(reactor.core.niso):
                if reactor.core.iso[i].print_xs:
                    fid[indx].write('time: ' + '{0:12.5e} '.format(time) + ' s\n')
                    nsig0 = len(reactor.core.iso[i].xs['tot'][0][0])
                    ntemp = len(reactor.core.iso[i].xs['tot'][0])
                    for itemp in range(ntemp):
                        fid[indx].write('total XS @' + '{0:12.5e} '.format(reactor.core.iso[i].temp[itemp]) + 'K \n')
                        fid[indx].write(' ' + 'igroup/sig0'.ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].sig0[isig0]) for isig0 in range(nsig0)]) + '\n')
                        for ig in range(reactor.core.ng):
                            fid[indx].write(' ' + str(ig+1).ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].xs['tot'][ig][itemp][isig0]) for isig0 in range(nsig0)]) + '\n')
                    if sum(reactor.core.iso[i].xs['chi']) > 0:
                        for itemp in range(ntemp):
                            fid[indx].write('fission XS @' + '{0:12.5e} '.format(reactor.core.iso[i].temp[itemp]) + 'K \n')
                            fid[indx].write(' ' + 'igroup/sig0'.ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].sig0[isig0]) for isig0 in range(nsig0)]) + '\n')
                            for ig in range(reactor.core.ng):
                                fid[indx].write(' ' + str(ig+1).ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].xs['fis'][ig][itemp][isig0]) for isig0 in range(nsig0)]) + '\n')
                        for itemp in range(ntemp):
                            fid[indx].write('nubar @' + '{0:12.5e} '.format(reactor.core.iso[i].temp[itemp]) + 'K \n')
                            fid[indx].write(' ' + 'igroup'.ljust(12) + '\n')
                            for ig in range(reactor.core.ng):
                                fid[indx].write(' ' + str(ig+1).ljust(12) + '{0:12.5e} '.format(reactor.core.iso[i].xs['nub'][ig][itemp]) + '\n')
                        fid[indx].write('fission spectrum\n')
                        fid[indx].write(' ' + 'igroup'.ljust(12) + 'chi'.ljust(12) + '\n')
                        for ig in range(reactor.core.ng):
                            fid[indx].write(' ' + str(ig+1).ljust(12) + '{0:12.5e} '.format(reactor.core.iso[i].xs['chi'][ig]) + '\n')

                    fid[indx].write('kerma-factors\n')
                    fid[indx].write(' ' + 'igroup/sig0'.ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].sig0[isig0]) for isig0 in range(nsig0)]) + '\n')
                    for ig in range(reactor.core.ng):
                        fid[indx].write(' ' + str(ig+1).ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].xs['kerma'][ig][isig0]) for isig0 in range(nsig0)]) + '\n')

                    for itemp in range(ntemp):
                        fid[indx].write('elastic scattering XS @' + '{0:12.5e} '.format(reactor.core.iso[i].temp[itemp]) + 'K \n')
                        fid[indx].write(' ' + 'from'.ljust(13) + 'to/sig0'.ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.iso[i].sig0[isig0]) for isig0 in range(nsig0)]) + '\n')
                        for s in reactor.core.iso[i].xs['ela']:
                            fid[indx].write(' ' + str(s[0][0]+1).ljust(13) + str(s[0][1]+1).ljust(12) + ''.join(['{0:12.5e} '.format(s[1][isig0]) for isig0 in range(nsig0)]) + '\n')

                    fid[indx].write('inelastic scattering XS\n')
                    fid[indx].write(' ' + 'from'.ljust(13) + 'to'.ljust(13) + 'sigi'.ljust(12) + '\n')
                    for s in reactor.core.iso[i].xs['ine']:
                        fid[indx].write(' ' + str(s[0][0]+1).ljust(13) + str(s[0][1]+1).ljust(12) + '{0:12.5e} '.format(s[1]) + '\n')
                    if len(reactor.core.iso[i].xs['n2n']) > 0:
                        fid[indx].write('n2n scattering\n')
                        fid[indx].write(' ' + 'from'.ljust(13) + 'to'.ljust(13) + 'sign2n'.ljust(12) + '\n')
                        for s in reactor.core.iso[i].xs['n2n']:
                            fid[indx].write(' ' + str(s[0][0]+1).ljust(13) + str(s[0][1]+1).ljust(12) + '{0:12.5e} '.format(s[1]) + '\n')
                    indx += 1
                    reactor.core.iso[i].print_xs = False
            for i in range(reactor.core.nmix):
                if reactor.core.mix[i].print_xs:
                    fid[indx].write('time: ' + '{0:12.5e} '.format(time) + ' s\n')
                    fid[indx].write('background XS\n')
                    fid[indx].write(' ' + 'igroup'.ljust(13) + ''.join([str(reactor.core.mix[i].isoid[j]).ljust(13) for j in range(reactor.core.mix[i].niso)]) + '\n')
                    for ig in range(reactor.core.ng):
                        fid[indx].write(' ' + str(ig+1).ljust(12) + ''.join(['{0:12.5e} '.format(reactor.core.mix[i].sig0[ig][j]) for j in range(reactor.core.mix[i].niso)]) + '\n')
                    fid[indx].write('total XS, production XS, fission spectrum, in-group scattering XS, out-group scattering XS, n2n XS, kerma-factors\n')
                    fid[indx].write(' ' + 'igroup'.ljust(13) + 'sigt'.ljust(13) + 'nu*sigf'.ljust(13) + 'chi'.ljust(13) + 'sigsi'.ljust(13) + 'sigso'.ljust(13) + 'sign2n'.ljust(13) + 'kerma'.ljust(13) + '\n')
                    for ig in range(reactor.core.ng):
                        sigso = 0
                        sigsi = 0
                        for j in range(len(reactor.core.mix[i].sigs)):
                            f = reactor.core.mix[i].sigs[j][0][0]
                            t = reactor.core.mix[i].sigs[j][0][1]
                            if f == ig and t != ig : sigso = sigso + reactor.core.mix[i].sigs[j][1]
                            if f == ig and t == ig : sigsi = sigsi + reactor.core.mix[i].sigs[j][1]
                        sign2n = 0
                        for j in range(len(reactor.core.mix[i].sign2n)):
                            f = reactor.core.mix[i].sign2n[j][0][0]
                            t = reactor.core.mix[i].sign2n[j][0][1]
                            if f == ig and t != ig : sign2n = sign2n + reactor.core.mix[i].sign2n[j][1]
                        fid[indx].write(' ' + str(ig+1).ljust(12) + str('{0:12.5e} '.format(reactor.core.mix[i].sigt[ig])) + str('{0:12.5e} '.format(reactor.core.mix[i].sigp[ig])) + str('{0:12.5e} '.format(reactor.core.mix[i].chi[ig])) + str('{0:12.5e} '.format(sigsi)) + str('{0:12.5e} '.format(sigso)) + str('{0:12.5e} '.format(sign2n)) + str('{0:12.5e} '.format(reactor.core.mix[i].kerma[ig])) + '\n')
                    fid[indx].write('scattering XS\n')
                    fid[indx].write(' ' + 'from'.ljust(13) + 'to'.ljust(13) + 'sigs'.ljust(13) + '\n')
                    for j in range(len(reactor.core.mix[i].sigs)):
                        f = reactor.core.mix[i].sigs[j][0][0] + 1
                        t = reactor.core.mix[i].sigs[j][0][1] + 1
                        sigs = reactor.core.mix[i].sigs[j][1]
                        fid[indx].write(' ' + str(f).ljust(13) + str(t).ljust(12) + '{0:12.5e} '.format(sigs) + '\n')
                    fid[indx].write('n2n XS\n')
                    fid[indx].write(' ' + 'from'.ljust(13) + 'to'.ljust(13) + 'sign2n'.ljust(13) + '\n')
                    for j in range(len(reactor.core.mix[i].sign2n)):
                        f = reactor.core.mix[i].sign2n[j][0][0] + 1
                        t = reactor.core.mix[i].sign2n[j][0][1] + 1
                        sign2n = reactor.core.mix[i].sign2n[j][1]
                        fid[indx].write(' ' + str(f).ljust(13) + str(t).ljust(12) + '{0:12.5e} '.format(sign2n) + '\n')
                    indx += 1
                    reactor.core.mix[i].print_xs = False

                else:
                    indx += 7
            # multiplication factor
            if flag == 0 : fid[indx].write(''.join([(' '+str(niter)).ljust(13) + '{0:12.5e} '.format(reactor.core.k[niter]) + '\n' for niter in range(len(reactor.core.k))]))
            indx += 1
            # neutron flux
            if flag == 0 : 
                for iz in range(reactor.core.nz):
                    for iy in range(reactor.core.ny):
                        for ix in range(reactor.core.nx):
                            imix = reactor.core.map['imix'][iz][iy][ix]
                            # if (ix, iy, iz) is not a boundary condition node, i.e. not -1 (vac) and not -2 (ref')
                            if imix >= 0:
                                for ig in range(reactor.core.ng):
                                    flux = sum([reactor.core.flux[iz][iy][ix][it][ig] for it in range(reactor.core.nt)])
                                    fid[indx].write('{0:12.5e} '.format(time) + ' ' + str(ig).ljust(13) + str(iz).ljust(13) + str(iy).ljust(13) + str(ix).ljust(12) + '{0:12.5e} '.format(flux) + '\n')
            indx += 1
            # power
            if flag == 0 : 
                for iz in range(reactor.core.nz):
                    for iy in range(reactor.core.ny):
                        for ix in range(reactor.core.nx):
                            imix = reactor.core.map['imix'][iz][iy][ix]
                            # if (ix, iy, iz) is not a boundary condition node, i.e. not -1 (vac) and not -2 (ref')
                            if imix >= 0 and reactor.core.pow[iz][iy][ix] > 0:
                                fid[indx].write('{0:12.5e} '.format(time) + ' ' + str(iz).ljust(13) + str(iy).ljust(13) + str(ix).ljust(12) + '{0:12.5e} '.format(reactor.core.pow[iz][iy][ix]) + '\n')
            indx += 1
            if flag == 0 : 
                for iy in range(reactor.core.ny):
                    for ix in range(reactor.core.nx):
                        if reactor.core.powxy[iy][ix] > 0:
                            fid[indx].write('{0:12.5e} '.format(time) + ' ' + str(iy).ljust(13) + str(ix).ljust(12) + '{0:12.5e} '.format(reactor.core.powxy[iy][ix]) + '\n')
            indx += 1

    #----------------------------------------------------------------------------------------------
    def write_to_y(self, reactor):

        # write list of unknowns to y
        y = []
        if 'fuelrod' in reactor.solve:
            for i in range(reactor.solid.nfuelrods):
                for j in range(reactor.solid.fuelrod[i].nz):
                    for k in range(reactor.solid.fuelrod[i].fuel[j].nr):
                        if 'fuelgrain' in reactor.solve and i + j + k == 0: #i+j+k==0 is a temporal condition to solve fuel grain only for one node
                            # fuel grain monoatoms
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].nr):
                                y.append(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].c1[l])
                            # fuel grain bubble radii
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                y.append(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].ri[l])
                            # fuel grain fractional concentration of irradiation-induced uranium vacancies
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                y.append(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].cv_irr[l])
                            # fuel grain fractional concentration of irradiation-induced uranium interstitials
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                y.append(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].ci_irr[l])
                            # fuel grain fractional concentration of uranium vacancies ejected from intragranular as-fabricated pores
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                y.append(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].cv_p[l])
                            # fuel grain intragranular bubble concentation
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                y.append(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].bi[l])
                    for k in range(reactor.solid.fuelrod[i].fuel[j].nr):
                        # fuel temperature
                        y.append(reactor.solid.fuelrod[i].fuel[j].temp[k])
                    for k in range(reactor.solid.fuelrod[i].clad[j].nr):
                        # clad temperature
                        y.append(reactor.solid.fuelrod[i].clad[j].temp[k])
        if 'fluid' in reactor.solve:
            for j in range(reactor.fluid.njun):
                if reactor.fluid.juntype[j] == 'independent':
                    # flowrate in independent junctions
                    y.append(reactor.fluid.mdoti[j])
            for i in range(reactor.fluid.npipe):
                for j in range(reactor.fluid.pipennodes[i]):
                    # temperature in pipe nodes
                    y.append(reactor.fluid.temp[i][j])
        if 'pointkinetics' in reactor.solve:
            y.append(reactor.core.power)
            for i in range(reactor.core.ndnp):
                y.append(reactor.core.cdnp[i])
        return y

    #----------------------------------------------------------------------------------------------
    def read_from_y(self, reactor, y):

        # read list of unknowns from y
        indx = 0
        if 'fuelrod' in reactor.solve:
            for i in range(reactor.solid.nfuelrods):
                for j in range(reactor.solid.fuelrod[i].nz):
                    for k in range(reactor.solid.fuelrod[i].fuel[j].nr):
                        if 'fuelgrain' in reactor.solve and i + j + k == 0:
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].nr):
                                # fuel grain monoatoms
                                reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].c1[l] = y[indx]
                                indx += 1
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                # fuel grain bubble radii
                                reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].rb[l] = y[indx]
                                indx += 1
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                # fuel grain fractional concentration of irradiation-induced uranium vacancies
                                reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].cv_irr[l] = y[indx]
                                indx += 1
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                # fuel grain fractional concentration of irradiation-induced uranium interstitials
                                reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].ci_irr[l] = y[indx]
                                indx += 1
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                # fuel grain fractional concentration of uranium vacancies ejected from intragranular as-fabricated pores
                                reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].cv_p[l] = y[indx]
                                indx += 1
                            for l in range(reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].NB):
                                # fuel grain intragranular bubble concentrations
                                reactor.solid.fuelrod[i].fuel[j].fuelgrain[k].bi[l] = y[indx]
                                indx += 1
                    for k in range(reactor.solid.fuelrod[i].fuel[j].nr):
                        # fuel temperature
                        reactor.solid.fuelrod[i].fuel[j].temp[k] = y[indx]
                        indx += 1
                    for k in range(reactor.solid.fuelrod[i].clad[j].nr):
                        # clad temperature
                        reactor.solid.fuelrod[i].clad[j].temp[k] = y[indx]
                        indx += 1
        if 'fluid' in reactor.solve:
            for j in range(reactor.fluid.njun):
                if reactor.fluid.juntype[j] == 'independent':
                    # flowrate in independent junctions
                    reactor.fluid.mdoti[j] = y[indx]
                    indx += 1
            for i in range(reactor.fluid.npipe):
                for j in range(reactor.fluid.pipennodes[i]):
                    # temperature in pipe nodes
                    reactor.fluid.temp[i][j] = y[indx]
                    indx += 1
        if 'pointkinetics' in reactor.solve:
            reactor.core.power = y[indx]
            indx += 1
            for i in range(reactor.core.ndnp):
                reactor.core.cdnp[i] = y[indx]
                indx += 1
