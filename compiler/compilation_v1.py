#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append("../pythonpddl")
import pddl
from antlr4 import *
import pddlLexer
import pddlParser
import itertools
from copy import deepcopy
# from random import randint

class CompilationParameters(object):
	"""	domain parameters to be compiled.
		Attributes:
		domain path: e.g '../expfiles/driverlog/domain.pddl'
		problem_path e.g '../expfiles/driverlog/pfile1.pddl'
		agentTypename e.g 'driver' or 'agent'
		agentTypeparameter e.g 'driver' in ?driver or 'a' in ?a
		waitlist, a list with the predicates to wait for when false.
				  e.g on-table
	"""
	print_condition = False
	fixADL = False

	def __init__(self):
		self.domain_path = ''
		self.problem_path = ''
		self.agentTypename = ''
		self.agentTypeparameter = ''
		self.waitlist = []
		self.agentslist = []

def grabFileAsList(file_address):
	new_list = []
	with open(file_address) as f:
		for line in f:
			new_list.append(line.rstrip())
	return new_list;

def MakeName(dom, prob):
	name = 'c' + dom.name
	return name;

def MakeReqs(dom, prob):
	reqs = deepcopy(dom.reqs)
	if not (u':fluents' in dom.reqs):
		reqs.append(u':fluents')
	if not (u':durative-actions' in dom.reqs):
		reqs.append(u':durative-actions')
	return reqs;

def MakeTypes(dom, prob):
	types =  deepcopy(dom.types)
	return types;

def MakeConstants(dom, prob):
	if prob is not None:
		constants = deepcopy(dom.constants)
		constants.args.extend(deepcopy(prob.objects.args))
	else:
		constants = deepcopy(dom.constants)
	# print 'the constants are:\n', constants.asPDDL()
	return constants;

def MakePredicates(dom, prob, params):
	predicates = []
	## fin, isnt-fin, act, failure
	predicates.append(pddl.Predicate(u'fin', pddl.TypedArgList([pddl.TypedArg( '?'+params.agentTypeparameter, params.agentTypename)])))
	# if params.fixADL:
	predicates.append(pddl.Predicate(u'isnt-fin', pddl.TypedArgList([pddl.TypedArg( '?'+params.agentTypeparameter, params.agentTypename)]))) # upgrade to ADL support
	predicates.append(pddl.Predicate(u'act', pddl.TypedArgList([])))
	predicates.append(pddl.Predicate(u'failure', pddl.TypedArgList([])))
	## local predicates
	for pred in dom.predicates:
		temp = deepcopy(pred)
		temp.name = temp.name + '-l'
		temp.args.args.insert(0, pddl.TypedArg(u'?alocal', params.agentTypename))
		predicates.append(temp)
	## global predicates
	for pred in dom.predicates:
		temp = deepcopy(pred)
		temp.name = temp.name + '-g'
		predicates.append(temp)
	## checked predicates
	for waitpred in params.waitlist:
		for pred in dom.predicates:
			if waitpred == pred.name:
				temp = deepcopy(pred)
				temp.name = temp.name + '-checked'
				predicates.append(temp)
	## waitfor predicates
	for waitpred in params.waitlist:
		for pred in dom.predicates:
			if waitpred == pred.name:
				temp = deepcopy(pred)
				temp.name = temp.name + '-wt'
				temp.args.args.insert(0, pddl.TypedArg(u'?alocal', params.agentTypename))
				predicates.append(temp)
				temp = deepcopy(pred)
				temp.name = temp.name + '-not-wt'
				temp.args.args.insert(0, pddl.TypedArg(u'?alocal', params.agentTypename))
				predicates.append(temp)
	if params.print_condition:
		print '\nthe predicates are :'
		for pred in predicates:
			print ' ', pred.asPDDL()
	return predicates;

def GrabCond(type, action, params):
	waitlist = params.waitlist
	if type == 'pref_start':
		pref_start = []
		for cond in action.get_cond('start', True):
			if cond.name not in waitlist:
				temp = deepcopy(cond)
				pref_start.append(temp)
		return pref_start
	elif type == 'prew_start':
		prew_start = []
		for cond in action.get_cond('start', True):
			if cond.name in waitlist:
				temp = deepcopy(cond)
				prew_start.append(temp)
		return prew_start
	elif type == 'pref_end':
		pref_end = deepcopy(action.get_cond('end', True))
		return pref_end
	elif type == 'pref_inv':
		pref_inv = deepcopy(action.get_cond('all', True))
		return pref_inv
	elif type == 'neg_pref_start':
		pref_start = []
		for cond in action.get_cond('start', False):
			if cond.name not in waitlist:
				temp = deepcopy(cond)
				pref_start.append(temp)
		return pref_start
	elif type == 'neg_prew_start':
		prew_start = []
		for cond in action.get_cond('start', False):
			if cond.name in waitlist:
				temp = deepcopy(cond)
				prew_start.append(temp)
		return prew_start
	elif type == 'neg_pref_end':
		pref_end = deepcopy(action.get_cond('end', False))
		return pref_end
	elif type == 'neg_pref_inv':
		pref_inv = deepcopy(action.get_cond('all', False))
		return pref_inv
	else:
		print 'error with type def'
		return;

def GrabEff(type, action):
	if not str(action.__class__) == 'pddl.DurativeAction':
		print 'argument 2 class is wrong'
		return None;
	elif type == 'add_start':
		add_start = deepcopy(action.get_eff('start', True))
		return add_start;
	elif type == 'del_start':
		del_start = deepcopy(action.get_eff('start', False))
		return del_start;
	elif type == 'add_end':
		add_end = deepcopy(action.get_eff('end', True))
		return add_end;
	elif type == 'del_end':
		del_end = deepcopy(action.get_eff('end', False))
		return del_end;
	else:
		print 'argument 1 is wrong'
		return None;

def MakeCond(time, predName, predArgs = []):
	""" time = 'start', 'end' ,'all'
		predName = the name of the condition as string e.g 'act'
		predArgs = list of the condition arguments e.g '['?a', '?c']'"""
	if len(predArgs) == 0: # the condition has no arguments
		cond = pddl.TimedFormula(time,
		pddl.Formula([pddl.Predicate(predName, pddl.TypedArgList([]))]))
		return cond;
	elif isinstance(predArgs[0], str):
		args = []
		for arg in deepcopy(predArgs):
			args.append(pddl.TypedArg(arg))
		cond = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(predName, pddl.TypedArgList(args))]))
		return cond;
	elif isinstance(predArgs[0], pddl.TypedArg):
		argslist = deepcopy(predArgs)
		cond = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(predName, pddl.TypedArgList(argslist))]))
		return cond;
	else:
		return;

def MakeNotWaitConds(pred, agents):
	# print 'the agents are: ', agents
	waitconds = []
	time = ['start', 'all', 'end']
	name = pred.name + '-not-wt'
	for t in time:
		for a in deepcopy(agents):
			args = [a] + pred.args.args
			# print 'time is: ', t, '  name is: ', name, '  args are: ', args
			waitconds.append(MakeCond(t, name, args))
	# print 'the waitconds are :',[w.asPDDL() for w in waitconds]
	return waitconds;

def MakeInvCond(time, pred):
	'''e.g time = 'start', pred = a predicate'''
	name = str(pred.name) + '-inv'
	args = ''
	for aname in pred.args.args:
		args = args + aname.arg_name + ' '
	st = '= (' + name + ' ' + args + ') 0 '
	return MakeCond(time, st)

def MakeInvEff(time, f, option, print_condition = False):
	if print_condition : print '\nRunning MakeInvEff'
	if option == 'increase':
		emptyargslist = pddl.TypedArgList([])
		name = 'increase (' + f.name + '-inv ' + f.args.asPDDL() + ') 1 '
		pred = pddl.Predicate(name, emptyargslist)
		subformulas = [ pred ]
		gd = pddl.Formula(subformulas)
		timespecifier = time
		eff = pddl.TimedFormula(timespecifier, gd)
		if print_condition : print '\ninv eff is: ', eff.asPDDL(), '\n'
		return eff
	elif option == 'decrease':
		emptyargslist = pddl.TypedArgList([])
		name = 'decrease (' + f.name + '-inv ' + f.args.asPDDL() + ') 1 '
		pred = pddl.Predicate(name, emptyargslist)
		subformulas = [ pred ]
		gd = pddl.Formula(subformulas)
		timespecifier = time
		eff = pddl.TimedFormula(timespecifier, gd)
		if print_condition : print '\ninv eff is: ', eff.asPDDL(), '\n'
		return eff

def MakeLocalCond(time, pred, params, op = None):
	agentTypeparameter = params.agentTypeparameter
	name = pred.name + '-l'
	args = deepcopy(pred.args.args)
	TypedArgName = '?' + agentTypeparameter
	arglist = pddl.TypedArgList([pddl.TypedArg(TypedArgName)] + args)
	if op == None:
		localcond = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, arglist)]))
	elif op == 'not':
		localcond = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, args)], 'not'))
	return localcond;

def MakeLocalEff(time, pred, params, positive = True):
	""" time = 'start','all','end'
	pred is a predicate
	positive = true if Eff is a add effect, false otherwise """
	agentTypeparameter = params.agentTypeparameter
	name = pred.name + '-l'
	args = deepcopy(pred.args.args)
	TypedArgName = '?'+ agentTypeparameter
	arglist = pddl.TypedArgList([pddl.TypedArg(TypedArgName)] + args)
	if positive:
		localEff = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, arglist)]))
	elif positive == False:
		localEff = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, arglist)], u'not'))
	return localEff

def MakeGlobalEff(time, pred, positive = True):
	""" time = 'start','all','end'
		pred is a predicate
		positive = true if Eff is a add effect, false otherwise """
	name = pred.name + '-g'
	arglist = deepcopy(pddl.TypedArgList(pred.args.args))
	if positive:
		globalEff = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, arglist)]))
	elif positive == False:
		globalEff = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, arglist)], u'not'))
	else:
		print 'error with positive var'
	return globalEff

def MakeGlobalCond(time, pred, op = None):
	name = pred.name + '-g'
	args = deepcopy(pred.args)
	if op == None:
		globalcond = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, args)]))
	elif op == 'not':
		globalcond = pddl.TimedFormula(time, pddl.Formula([pddl.Predicate(name, args)], 'not'))
	return globalcond;

def GetAgents(constants, params):
	agentTypename = params.agentTypename
	agents = []
	for x in deepcopy(constants.args):
		if x.arg_type == agentTypename:
			agents.append(x)
	# remove type indication (cosmetics)
	for i in range(len(agents)):
		agents[i].arg_type = None
	return agents;

def MakeConds_s(action, constants, params):
	waitlist = params.waitlist
	agentTypename =  params.agentTypename
	agentTypeparameter =  params.agentTypeparameter
	print_condition = params.print_condition
	conds = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# build pref_start conditions to action
	conds.append(MakeCond('start','act'))
	for f in pref_start:
		conds.append(MakeLocalCond('start',f, params))
		conds.append(MakeGlobalCond('start', f))
	for f in prew_start:
		conds.append(MakeLocalCond('start',f, params))
		conds.append(MakeGlobalCond('start', f))
	for f in del_start:
		conds.append(MakeInvCond('start', f))
	# build pref_inv conditions to action
	conds.append(MakeCond('all','act'))
	for f in pref_inv:
		conds.append(MakeLocalCond('all',f, params))
		conds.append(MakeGlobalCond('all', f))
	# build pref_end conditions to action
	conds.append(MakeCond('end','act'))
	for f in pref_end:
		conds.append(MakeLocalCond('end',f, params))
		conds.append(MakeGlobalCond('end', f))
	for f in del_end:
		conds.append(MakeInvCond('end', f))
	# build wait conds
	waitconds = []
	agents = GetAgents(constants, params)
	# print 'list of agents: ',[a.asPDDL() for a in agents]
	for f in add_start + add_end:
		if f.name in waitlist:
			# print f, ': ', f.asPDDL() , ' is in wait list'
			waitconds = waitconds + MakeNotWaitConds(f, agents)
	conds += waitconds
	if print_condition:
		print '\nthe conditions are:'
		for cond in conds:
			print cond.asPDDL()
	return conds

def MakeActions_s(action, constants, params):
	waitlist = params.waitlist
	agentTypename =  params.agentTypename
	agentTypeparameter =  params.agentTypeparameter
	print_condition = params.print_condition
	name = action.name + '-s'
	parameters = deepcopy(action.parameters)
	duration_lb = action.duration_lb
	duration_ub = action.duration_ub
	conds = MakeConds_s(action, constants, params)
	effs = MakeEffs_s(action, constants, params)
	action_s = pddl.DurativeAction(name, parameters, duration_lb, duration_ub, conds, effs)
	return action_s;

def MakeEffs_s(action, constants, params):
	waitlist = params.waitlist
	agentTypename =  params.agentTypename
	agentTypeparameter =  params.agentTypeparameter
	print_condition = params.print_condition
	effs = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# if print_condition:
	#     print '\nadd start effects are: ',[a.asPDDL() for a in add_start]
	#     print 'del start effects are: ',[a.asPDDL() for a in del_start]
	#     print 'add end effects are: ',[a.asPDDL() for a in add_end]
	#     print 'del end effects are: ',[a.asPDDL() for a in del_end], '\n'
	#     print '\npref_start conds are: ',[a.asPDDL() for a in pref_start]
	#     print 'prew_start conds are: ',[a.asPDDL() for a in prew_start]
	#     print 'pref_inv are: ',[a.asPDDL() for a in pref_inv]
	#     print 'pref_end are: ',[a.asPDDL() for a in pref_end], '\n'
	## add start effects
	for f in add_start: # f_i, f_g | f E add_start(a)
		effs.append(MakeLocalEff(u'start', f, params, True))
		effs.append(MakeGlobalEff(u'start', f, True))
	for f in pref_inv: # f-inv ++ | f E pre_inv(a)
		effs.append(MakeInvEff(u'start', f, 'increase'))
	## del start effects
	for f in del_start:
		effs.append(MakeLocalEff(u'start', f, params, False))
		effs.append(MakeGlobalEff(u'start', f, False))
	## add end effects
	for f in add_end: # f_i, f_g | f E add_end(a)
		effs.append(MakeLocalEff(u'end', f, params, True))
		effs.append(MakeGlobalEff(u'end', f, True))
	## del end effects
	for f in del_end: # f_i, f_g | f E del_end(a)
		effs.append(MakeLocalEff(u'end', f, params, False))
		effs.append(MakeGlobalEff(u'end', f, False))
	for f in pref_inv:
		effs.append(MakeInvEff(u'end', f, 'decrease'))

	# print effects
	if print_condition:
		if len(effs) == 0:
			print 'there are no effects'
		else:
			print '\nthe effects are:'
			for eff in effs:
				print eff.asPDDL()
	return effs;

def MakeActions_fstart(action, constants, params):
	waitlist =  params.waitlist
	print_condition = params.print_condition
	pref_start = GrabCond('pref_start', action, params)
	Actions_fstart = []
	for i in range(len(pref_start)):
	# for i in range(2): # for test only
		Action_fstart_i = MakeAction_fstart_i(action, constants, params, i)
		Actions_fstart.append(Action_fstart_i)
	return Actions_fstart;

def MakeAction_fstart_i(action, constants, params, i):
	waitlist = params.waitlist
	print_condition = params.print_condition
	pref_start = GrabCond('pref_start', action, params)
	name = action.name + '-f-start-' + str(i+1)
	parameters = deepcopy(action.parameters)
	duration_lb = action.duration_lb
	duration_ub = action.duration_ub
	if print_condition:
		print '\naction_fstart name is: ', name
		print 'action_fstart parameters are: ', parameters.asPDDL()
	conds = MakeConds_fstart(action, constants, params, i)
	effs = MakeEffs_fstart(action, constants, params)
	Action_fstart_i = pddl.DurativeAction(name, parameters, duration_lb, duration_ub, conds, effs)
	return Action_fstart_i;

def MakeEffs_fstart(action, constants, params):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	effs = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# if print_condition:
	#     print '\nadd start effects are: ',[a.asPDDL() for a in add_start]
	#     print 'del start effects are: ',[a.asPDDL() for a in del_start]
	#     print 'add end effects are: ',[a.asPDDL() for a in add_end]
	#     print 'del end effects are: ',[a.asPDDL() for a in del_end], '\n'
	#     print '\npref_start conds are: ',[a.asPDDL() for a in pref_start]
	#     print 'prew_start conds are: ',[a.asPDDL() for a in prew_start]
	#     print 'pref_inv are: ',[a.asPDDL() for a in pref_inv]
	#     print 'pref_end are: ',[a.asPDDL() for a in pref_end], '\n'
	# add start effects
	effs.append(MakeEff(u'start', u'failure', [])) ## {failure}
	for f in add_start: ## {f_i V f e add_start(a)}
		effs.append(MakeLocalEff(u'start', f,  params,True))
	# del_start effects
	for f in del_start: ## {f_i V f e del_start(a)}
		effs.append(MakeLocalEff(u'start', f, params, False))
	# add_end effects
	for f in add_end: ## {f_i V f e add_end(a)}
		effs.append(MakeLocalEff(u'end', f, params, True))
	# del_end
	for f in del_end: ## {f_i V f e del_end(a)}
		effs.append(MakeLocalEff(u'end', f, params, False))
	# print effects
	if print_condition:
		if len(effs) == 0:
			print 'there are no effects'
		else:
			print '\nthe effects are:'
			for eff in effs:
				print ' ',eff.asPDDL()
	return effs;

def MakeEff(time, effName, effdArgs = []):
	""" time = 'start', 'end' ,'all'
	effName = the name of the effect as string e.g 'failure'
	effdArgs = list of the effect arguments e.g '['?a', '?c']'"""
	# effdArgs = ['?a', '?c']
	# effName = 'Hold-Cup'
	# time = 'start'
	args = []
	for arg in effdArgs:
		args.append(deepcopy(pddl.TypedArg(arg)))
	argslist = pddl.TypedArgList(args)
	subformulas = [ pddl.Predicate(effName, argslist) ]
	formula = pddl.Formula(subformulas, op = None) # subformulas: list of pddl.Predicate
	eff = pddl.TimedFormula(time, formula)
	return eff

def MakeConds_fstart(action, constants, params, i):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	conds = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	if print_condition:
		print '\nadd start effects are: ',[a.asPDDL() for a in add_start]
		print 'del start effects are: ',[a.asPDDL() for a in del_start]
		print 'add end effects are: ',[a.asPDDL() for a in add_end]
		print 'del end effects are: ',[a.asPDDL() for a in del_end], '\n'
		print '\npref_start conds are: ',[a.asPDDL() for a in pref_start]
		print 'prew_start conds are: ',[a.asPDDL() for a in prew_start]
		print 'pref_inv are: ',[a.asPDDL() for a in pref_inv]
		print 'pref_end are: ',[a.asPDDL() for a in pref_end], '\n'
	# build pref_start conditions to action
	conds.append(MakeCond('start','act'))
	for f in prew_start:
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))
	for f in pref_start:
		conds.append(MakeLocalCond('start', f, params))
	if print_condition: print '\nf to be inverted is: ', pref_start[i].name , '-g'
	conds.append(MakeGlobalCond('start', pref_start[i], 'not'))
	# build pref_inv conditions to action
	conds.append(MakeCond('all','act'))
	for f in pref_inv:
		conds.append(MakeLocalCond('all',f, params))
	# build pref_end conditions to action
	conds.append(MakeCond('end','act'))
	for f in pref_end:
		conds.append(MakeLocalCond('end', f, params))
	# print list of conds
	if print_condition:
		print '\nthe conditions are:'
		for f in conds:
			print ' ', f.asPDDL()
	return conds;

def FixADLConds(conds):
	print_condition = False
	# get conds as a list of timedformula
	# make a copy
	# loop over all the conds
	# where there is a not condition add 'isnt-' to the name
	# remove the not condition
	fixedconds = deepcopy(conds)
	for cond in fixedconds:
		if cond.formula.op == 'not':
			if print_condition:
				print cond.asPDDL(), ' has a not condition'
			if cond.formula.subformulas[0].name.startswith('isnt'):
				cond.formula.op = None
				cond.formula.subformulas[0].name = cond.formula.subformulas[0].name[5:]
			else:
				cond.formula.op = None
				cond.formula.subformulas[0].name = 'isnt-' + cond.formula.subformulas[0].name
			if print_condition:
				print cond.asPDDL(), ' is the new condition'
	return fixedconds;

def MakeActions_fend(action, constants, params):
	waitlist =  params.waitlist
	print_condition = params.print_condition
	pref_end = GrabCond('pref_end', action, params)
	Actions_fend = []
	for i in range(len(pref_end)):
		Action_fend_i = MakeAction_fend_i(action, constants, params, i)
		Actions_fend.append(Action_fend_i)
	return Actions_fend;

def MakeAction_fend_i(action, constants, params, i):
	waitlist =  params.waitlist
	print_condition = params.print_condition
	pref_end = GrabCond('pref_start', action, params)
	name = action.name + '-f-end-' + str(i+1)
	parameters = deepcopy(action.parameters)
	duration_lb = action.duration_lb
	duration_ub = action.duration_ub
	if print_condition:
		print '\naction_fend name is: ', name
		print 'action_fend parameters are: ', parameters.asPDDL()
	conds = MakeConds_fend(action, constants, params, i)
	effs = MakeEffs_fend(action, constants, params)
	Action_fend_i = pddl.DurativeAction(name, parameters, duration_lb, duration_ub, conds, effs)
	return Action_fend_i;

def MakeEffs_fend(action, constants, params):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	effs = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# if print_condition:
	#     print '\nadd start effects are: ',[a.asPDDL() for a in add_start]
	#     print 'del start effects are: ',[a.asPDDL() for a in del_start]
	#     print 'add end effects are: ',[a.asPDDL() for a in add_end]
	#     print 'del end effects are: ',[a.asPDDL() for a in del_end], '\n'
	#     print '\npref_start conds are: ',[a.asPDDL() for a in pref_start]
	#     print 'prew_start conds are: ',[a.asPDDL() for a in prew_start]
	#     print 'pref_inv are: ',[a.asPDDL() for a in pref_inv]
	#     print 'pref_end are: ',[a.asPDDL() for a in pref_end], '\n'

	# add start effects
	for f in add_start: ## {f_i, f_g V f e add_start(a)}
		effs.append(MakeLocalEff(u'start', f, params, True))
		effs.append(MakeGlobalEff(u'start', f, True))
	# del_start effects
	for f in del_start: ## {f_i, f_g V f e add_del(a)}
		effs.append(MakeLocalEff(u'start', f, params, False))
		effs.append(MakeGlobalEff(u'start', f, False))
	# add_end effects
	for f in add_end:
		effs.append(MakeLocalEff(u'end', f, params, True)) ## {f_i V f e add_end(a)}
	effs.append(MakeEff(u'end', u'failure', [])) ## {failure}
	# del_end
	for f in del_end: ## {f_i V f e del_end(a)}
		effs.append(MakeLocalEff(u'end', f, params, False))
	# print effects
	if print_condition:
		if len(effs) == 0:
			print 'there are no effects'
		else:
			print '\nthe effects are:'
			for eff in effs:
				print ' ',eff.asPDDL()
	return effs;

def MakeConds_fend(action, constants, params, i):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	conds = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# build pref_start conditions to action
	conds.append(MakeCond('start','act')) ## {act}
	for f in pref_start: ## {f_i, f_g V f e pref_start(a)}
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))
	for f in prew_start: ## {f_i, f_g V f e prew_start(a)}
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))
	# build pref_inv conditions to action
	conds.append(MakeCond('all','act')) ## {act}
	for f in pref_inv: ## {f_i, f_g V f e pref_inv(a)}
		conds.append(MakeLocalCond('all', f, params))
		conds.append(MakeGlobalCond('all', f))
	# build pref_end conditions to action
	conds.append(MakeCond('end','act')) ## {act}
	for f in pref_end: ## {f_i V f e pref_end(a)}
		conds.append(MakeLocalCond('end', f, params))
	## {not f_g(i) V f e pref_end(a)}
	if print_condition: print 'f to be inverted is: ', pref_end[i].name , '-g'
	conds.append(MakeGlobalCond('end', pref_end[i], 'not'))
	# print list of conds
	if print_condition:
		print '\nthe conditions are:'
		for f in conds:
			print ' ', f.asPDDL()
	return conds;

def MakeFunctions(dom, prob, params):
	waitlist = params.waitlist
	print_condition = params.print_condition
	funcs = []
	preds = deepcopy(dom.predicates)
	for pred in preds:
		name = pred.name + '-inv'
		args = pred.args
		func = pddl.Function(name, args)
		funcs.append(func)
	if print_condition:
		print '\nthe following functions were composed:'
		for func in funcs:
			print ' ', func.asPDDL()
	return funcs;

def MakeAction_finv_start(action, constants, params):
	waitlist = params.waitlist
	print_condition = params.print_condition
	del_start = GrabEff('del_start', action)
	if len(del_start) == 0:
		if print_condition: print 'del_start is empty'
		return None;
	if print_condition: print '\n'*5
	name = action.name + '-f-inv-start'
	parameters = deepcopy(action.parameters)
	duration_lb = action.duration_lb
	duration_ub = action.duration_ub
	conds = MakeConds_finv_start(action, constants, params)
	effs = MakeEffs_finv_start(action, constants, params)
	action_finv_start = pddl.DurativeAction(name, parameters, duration_lb, duration_ub, conds, effs)
	return action_finv_start;

def MakeConds_finv_start(action, constants, params):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	conds = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# build pref_start conditions to action
	conds.append(MakeCond('start','act')) ## {act}
	## {f_i, f_g V pref_start}
	for f in pref_start:
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))
	## {f_i, f_g V prew_start}
	for f in prew_start:
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))
	## {sum(f_inv) > 0 V f e del(a)}
	conds.append(MakefinvSumCond(del_start, 'start'))
	# build pref_inv conditions to action
	## {act}
	conds.append(MakeCond('all','act'))
	## {f_i V f e pref_inv}
	for f in pref_inv:
		conds.append(MakeLocalCond('all', f, params))
	# build pref_end conditions to action
	## {act}
	conds.append(MakeCond('end','act'))
	## {f_i V f e pref_end}
	for f in pref_end:
		conds.append(MakeLocalCond('end', f, params))
	if print_condition:
		print '\nthe following conditions were composed:'
		for cond in conds:
			print ' ', cond.asPDDL()
	return conds;

def MakeEffs_finv_start(action, constants, params):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	effs = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	## add start effects
	for f in add_start: # {f_i V f e add_start}
		effs.append(MakeLocalEff(u'start', f, params, True))
	effs.append(MakeEff(u'start', u'failure', [])) # {failure}
	## del start effects
	for f in del_start: # {f_i V f e del_start}
		effs.append(MakeLocalEff(u'start', f, params, False))
	## add end effects
	for f in add_end: # {f_i V f e add_end}
		effs.append(MakeLocalEff(u'end', f, params, True))
	## del end effects
	for f in del_end: # {f_i V f e del_end}
		effs.append(MakeLocalEff(u'end', f, params, False))
	# print effects
	if print_condition:
		if len(effs) == 0:
			print 'there are no effects'
		else:
			print '\nthe effects are:'
			for eff in effs:
				print ' ',eff.asPDDL()
	return effs;

def MakeAction_finv_end(action, constants, params):
	waitlist = params.waitlist
	print_condition = params.print_condition
	del_end = GrabEff('del_end', action)
	if len(del_end) == 0:
		if print_condition: print '\ndel_end is empty\n'
		return None;
	if print_condition:
		print '\n'*5
		print 'del_end effects are: ', [f.asPDDL() for f in del_end]
	name = action.name + '-f-inv-end'
	parameters = deepcopy(action.parameters)
	duration_lb = action.duration_lb
	duration_ub = action.duration_ub
	conds = MakeConds_finv_end(action, constants, params)
	effs = MakeEffs_finv_end(action, constants, params)
	action_finv_start = pddl.DurativeAction(name, parameters, duration_lb, duration_ub, conds, effs)
	return action_finv_start;

def MakeConds_finv_end(action, constants, params):
	waitlist = params.waitlist
	agentTypeparameter = params.agentTypeparameter
	print_condition = params.print_condition
	conds = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# build pref_start conditions to action
	conds.append(MakeCond('start','act')) ## {act}
	for f in pref_start:
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))  ## {f_i, f_g V f e pref_start}
	for f in prew_start:
		conds.append(MakeLocalCond('start', f, params))
		conds.append(MakeGlobalCond('start', f))  ## {f_i, f_g V f e prew_start}
	for f in del_start:
		conds.append(MakeInvCond('start', f))  ## {f_inv = 0 V f e del_start}
	# build pref_inv conditions to action
	conds.append(MakeCond('all','act'))  ## {act}
	for f in pref_inv:
		conds.append(MakeLocalCond('all', f, params))
		conds.append(MakeGlobalCond('all', f))  ## {f_i, f_g V f e pref_inv}
	# build pref_end conditions to action
	conds.append(MakeCond('end','act'))  ## {act}
	for f in pref_end:
		conds.append(MakeLocalCond('end', f, params))
		conds.append(MakeGlobalCond('end', f))  ## {f_i, f_g V f e pref_inv}
	conds.append(MakefinvSumCond(del_end, 'end'))  ## {sum of f_inv V f e del_end > 0}
	# print effects
	if print_condition:
		print '\nthe conditions are:'
		for f in conds:
			print ' ', f.asPDDL()
	return conds;

def MakeEffs_finv_end(action, constants, params):
	waitlist = params.waitlist
	agentTypeparameter =params.agentTypeparameter
	print_condition = params.print_condition
	effs = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	## add start effects
	for f in add_start:
		effs.append(MakeLocalEff(u'start', f, params, True))
		effs.append(MakeGlobalEff(u'start', f, True))  ## {f_i, f_g V f e add_start}
	for f in pref_inv:
		effs.append(MakeInvEff(u'start', f, 'increase'))  ## {f_inv ++ V f e pre_inv}
	## del start effects
	for f in del_start:
		effs.append(MakeLocalEff(u'start', f, params, False))
		effs.append(MakeGlobalEff(u'start', f, False))  ## {f_i, f_g V f e del_start}
	## add end effects
	for f in add_end:
		effs.append(MakeLocalEff(u'end', f, params, True))  ## {f_i V f e add_end}
	effs.append(MakeEff(u'end', u'failure', []))  ## {failure}
	## del end effects
	for f in del_end:
		effs.append(MakeLocalEff(u'end', f, params, False))  ## {f_i V f e del_end}
	# print effects
	if print_condition:
		if len(effs) == 0:
			print '\nthere are no effects'
		else:
			print '\nthe effects are:'
			for eff in effs:
				print ' ',eff.asPDDL()
	return effs;

def MakefinvSumCond(predlist, time):
	def Make_sumPred(f_1, f_2):
		name = '+ ' + f_1.asPDDL() + ' ' + f_2.asPDDL()
		emptyargslist = pddl.TypedArgList([])
		sumPred = pddl.Predicate(name, emptyargslist)
		return sumPred;
	f_invs = deepcopy(predlist)
	for f in f_invs:
		f.name = f.name + '-inv'
	if len(f_invs) == 1:
		name = '> ' + f_invs[0].asPDDL() + ' 0'
		sumCond = MakeCond(time, name, [])
		# print sumCond.asPDDL()
		return sumCond
	elif len(f_invs) >= 2:
		sumPred = Make_sumPred(f_invs.pop(), f_invs.pop())
		while len(f_invs) > 0:
			sumPred = Make_sumPred(sumPred, f_invs.pop())
		# print sumPred.asPDDL()
		name = '> ' + sumPred.asPDDL() + ' 0'
		sumCond = MakeCond(time, name, [])
		# print sumCond.asPDDL()
		return sumCond

def MakeActions_Wait(action, constants, params):
	waitlist = params.waitlist
	print_condition = params.print_condition
	prew_start = GrabCond('prew_start', action, params)
	if len(prew_start) == 0:
		if print_condition: print 'there are no prew_start conds'
		return [];
	actions_wait = []
	for waitcond in prew_start:
		name = action.name + '-wait-' + waitcond.name
		if print_condition: print 'the name of the action is: ', name
		parameters = deepcopy(action.parameters)
		duration_lb = action.duration_lb
		duration_ub = action.duration_ub
		conds = MakeConds_wait(action, waitcond, params)
		effs = MakeEffs_wait(action, waitcond, constants, params)
		action_wait = pddl.DurativeAction(name, parameters, duration_lb, duration_ub, conds, effs)
		actions_wait.append(action_wait)
	return actions_wait;

def MakeConds_wait(action, waitcond, params):
	waitlist = params.waitlist
	agentTypeparameter =params.agentTypeparameter
	print_condition = params.print_condition
	conds = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# build pref_start conditions to action
	conds.append(MakeCond('start','act')) ## {act}
	for f in pref_start:
		conds.append(MakeLocalCond('start', f, params)) ## {f_i V f e pref_start}
	for f in prew_start:
		conds.append(MakeLocalCond('start', f, params)) ## {f_i V f e prew_start}
	conds.append(MakeGlobalCond('start', waitcond, 'not')) ## {not f_g V f e prew_start}
	# build pref_inv conditions to action
	conds.append(MakeCond('all','act')) ## {act}
	for f in pref_inv:
		conds.append(MakeLocalCond('all', f, params)) ## {f_i V f e pref_inv}
	# build pref_end conditions to action
	conds.append(MakeCond('end','act')) ## {act}
	for f in pref_end:
		conds.append(MakeLocalCond('end', f, params)) ## {f_i  V f e pref_inv}
	# print effects
	if print_condition:
		print '\nthe conditions are:'
		for f in conds:
			print ' ', f.asPDDL()
	return conds;

def MakeWaitEffect(waitcond, time, positive, params):
	args = [pddl.TypedArg('?'+params.agentTypeparameter)] + waitcond.args.args
	argslist = pddl.TypedArgList(args)
	if positive:
		effName = waitcond.name + '-wt'
	else:
		effName = waitcond.name + '-not-wt'
	subformulas = [ pddl.Predicate(effName, argslist) ]
	if positive:
		formula = pddl.Formula(subformulas, op = None) # subformulas: list of pddl.Predicate
	else:
		formula = pddl.Formula(subformulas, 'not') # subformulas: list of pddl.Predicate
	wtEff = deepcopy(pddl.TimedFormula(time, formula))
	return wtEff;

def MakeEffs_wait(action, waitcond, constants, params):
	waitlist = params.waitlist
	agentTypeparameter =params.agentTypeparameter
	print_condition = params.print_condition
	effs = []
	# grab basic conditions
	pref_start = GrabCond('pref_start', action, params)
	prew_start = GrabCond('prew_start', action, params)
	pref_inv = GrabCond('pref_inv', action, params)
	pref_end = GrabCond('pref_end', action, params)
	# grab basic effects
	add_start = GrabEff('add_start', action)
	del_start = GrabEff('del_start', action)
	add_end = GrabEff('add_end', action)
	del_end = GrabEff('del_end', action)
	# add start effects
	effs.append(MakeEff(u'start', u'failure', [])) ## {failure}
	for f in add_start:
		effs.append(MakeLocalEff(u'start', f, params, True))    ##{f_i V f e add_start}
	# {f-wt}
	effs.append(MakeWaitEffect(waitcond, 'start', True, params))
	# del_start effects
	for f in del_start: # {f_i V f e del_start}
		effs.append(MakeLocalEff(u'start', f, params, False))
	# { f-not-wt }
	effs.append(MakeWaitEffect(waitcond, 'start', False, params))
	# add_end effects
	for f in add_end: ## {f_i V f e add_end(a)}
		effs.append(MakeLocalEff(u'end', f, params, True))

	# del_end effects
	for f in del_end: ## {f_i V f e del_end(a)}
		effs.append(MakeLocalEff(u'end', f, params, False))
	# print effects
	if print_condition:
		if len(effs) == 0:
			print 'there are no effects'
		else:
			print '\nthe effects are:'
			for eff in effs:
				print ' ',eff.asPDDL()
	return effs;

def MakeActions_end_s(dom, prob, params):
	''' get agent list e.g [person1, person2]
		dom is pddl.Domain
		prob is pddl.Problem
		returns end_s_actions as list of actions
	'''
	print_condition = params.print_condition
	agentslist = params.agentslist
	if print_condition: print '\n'
	end_s_actions = []
	for name in agentslist:
		action_name = 'end-' + name + '-s'
		parameters = pddl.TypedArgList([])
		pre = MakeConds_end_s(prob, name, params)
		effs = MakeEffs_end_s(name, params)
		end_s = pddl.Action(action_name, parameters, pre, effs)
		end_s_actions.append(end_s)
	if print_condition:
		print '\ncomposed ', len(end_s_actions), ' end_s actions as following:'
		for i in range(len(end_s_actions)):
			print '\nthe (', i+1 ,') action is: \n', end_s_actions[i].asPDDL()
	return end_s_actions;

def MakeConds_end_s(prob, name, params):
	agentslist = params.agentslist
	print_condition = params.print_condition
	subformulas = [] #list of predicates
	# {not fin_i}
	argslist = pddl.TypedArgList([pddl.TypedArg(name)])
	pred = pddl.Predicate('isnt-fin', argslist)
	subformulas.append(pred)
	# {f_g, f_i forall f e G_i}
	agent_goals = GrabGoals(prob, name, params)
	for goal in agent_goals:
		local_name = goal.name + '-l'
		local_args = [pddl.TypedArg(name)] + goal.args.args
		local_argslist = pddl.TypedArgList(local_args)
		local_pred = pddl.Predicate(local_name, local_argslist)
		subformulas.append(deepcopy(local_pred))
		global_name = goal.name + '-g'
		global_args = goal.args.args
		global_argslist = pddl.TypedArgList(global_args)
		global_pred = pddl.Predicate(global_name, global_argslist)
		subformulas.append(deepcopy(global_pred))
	pre = pddl.Formula(subformulas, "and")
	if print_condition:
		print '\nthe composed conditions for end_s are:'
		print pre.asPDDL()
	return pre;

def MakeEffs_end_s(name, params):
	print_condition = params.print_condition
	effs = []
	# fin_i + not(isnt-fin)
	fin_args = [pddl.TypedArg(name)]
	fin_argslist = pddl.TypedArgList(fin_args)
	fin_subformulas = [pddl.Predicate('fin', fin_argslist)]
	fin_eff = pddl.Formula(fin_subformulas)
	effs.append(fin_eff)
	# not isnt-fin
	isnt_fin_subformulas = [pddl.Predicate('isnt-fin', fin_argslist)]
	isnt_fin_eff = pddl.Formula(isnt_fin_subformulas, 'not')
	effs.append(isnt_fin_eff)
	# del act
	act_argslist = pddl.TypedArgList([])
	act_subformulas = [pddl.Predicate('act', act_argslist)]
	act_eff = pddl.Formula(act_subformulas, 'not')
	effs.append(act_eff)
	if print_condition:
		print '\ncomposed the following effects to action end-',name,'-s'
		for eff in effs:
			print ' ', eff.asPDDL()
	return effs;

def get_first_common_element(x,y):
	''' Fetches first element from x that is common for both lists
		or return None if no such an element is found.
	'''
	for i in x:
		if i in y:
			return i
	return None

def GrabGoals(prob, name, params):
	''' grabs the goals from prob and returns them as list of predicates.'''
	agentslist = params.agentslist
	print_condition = params.print_condition
	preds = []
	for form in prob.goal.subformulas:
		if form.op != None or len(form.subformulas) != 1:
			print 'there is a problen with goal description'
			return
		else:
			if len(form.subformulas[0].args.args) == 0:
				preds.append(deepcopy(form.subformulas[0]))
			else:
				arg_list = map(lambda x: x.arg_name, form.subformulas[0].args.args)
				if name in arg_list: # if at least one arg is the named agent -> this is a goal
					preds.append(deepcopy(form.subformulas[0]))
				elif get_first_common_element(arg_list, agentslist) == None: # if all args are objects who are not agents -> this is a goal
					preds.append(deepcopy(form.subformulas[0]))
	if print_condition:
		print '\nthe goals of ',name,' are:'
		print ' '.join(map(lambda x: x.asPDDL(), preds))
	return preds;

def MakeConds_end_f_old(prob, name, inverse_goal, params):
	agentslist = params.agentslist
	print_condition = params.print_condition
	subformulas = []
	# {not fin_i}
	argslist = pddl.TypedArgList([pddl.TypedArg(name)])
	pred = pddl.Predicate('isnt-fin', argslist)
	subformulas.append(pred)
	# {f_i forall f e G_i}
	agent_goals = GrabGoals(prob, name, params)
	for goal in agent_goals:
		local_name = goal.name + '-l'
		local_args = [pddl.TypedArg(name)] + goal.args.args
		local_argslist = pddl.TypedArgList(local_args)
		local_pred = pddl.Predicate(local_name, local_argslist)
		subformulas.append(deepcopy(local_pred))
	# {there is a not(f_g) for f e G_i}
	if inverse_goal.name.startswith('isnt-'):
		inverse_goal_name = inverse_goal.name[5:] + '-g'
	else:
		inverse_goal_name = 'isnt-' + inverse_goal.name + '-g'
	inverse_goal_pred = pddl.Predicate(inverse_goal_name, inverse_goal.args )
	subformulas.append(deepcopy(inverse_goal_pred))
	pre = pddl.Formula(subformulas, "and")
	# print conditions :
	if print_condition:
		print '\nthe composed conditions for end_f are:'
		print pre.asPDDL()
	return pre;

def MakeConds_end_f(prob, name, inverse_goal, params):
	agentslist = params.agentslist
	print_condition = params.print_condition
	subformulas = []
	# {not fin_i}
	argslist = pddl.TypedArgList([pddl.TypedArg(name)])
	pred = pddl.Predicate('isnt-fin', argslist)
	form = pddl.Formula([pred], None)
	subformulas.append(form)
	# {f_i forall f e G_i}
	agent_goals = GrabGoals(prob, name, params)
	for goal in agent_goals:
		local_name = goal.name + '-l'
		local_args = [pddl.TypedArg(name)] + goal.args.args
		local_argslist = pddl.TypedArgList(local_args)
		local_pred = pddl.Predicate(local_name, local_argslist)
		local_form = pddl.Formula([local_pred], None)
		subformulas.append(deepcopy(local_form))
	# {there is a not(f_g) for f e G_i}
	inverse_goal_name = inverse_goal.name + '-g'
	inverse_goal_pred = pddl.Predicate(inverse_goal_name, inverse_goal.args )
	inverse_goal_form = pddl.Formula([inverse_goal_pred], 'not')
	subformulas.append(inverse_goal_form)
	# print and return conditions.
	pre = pddl.Formula(subformulas, "and")
	# print conditions :
	if print_condition:
		print '\nthe composed conditions for end_f are:'
		print pre.asPDDL()
	return pre;

def MakeEffs_end_f(name, print_condition):
	effs = []
	# failure
	failure_subformulas = [pddl.Predicate(u'failure', pddl.TypedArgList([]))]
	failure_eff = pddl.Formula(failure_subformulas)
	effs.append(failure_eff)
	# fin_i + not(isnt-fin)
	fin_args = [pddl.TypedArg(name)]
	fin_argslist = pddl.TypedArgList(fin_args)
	fin_subformulas = [pddl.Predicate('fin', fin_argslist)]
	fin_eff = pddl.Formula(fin_subformulas)
	effs.append(fin_eff)
	# not isnt-fin
	isnt_fin_subformulas = [pddl.Predicate('isnt-fin', fin_argslist)]
	isnt_fin_eff = pddl.Formula(isnt_fin_subformulas, 'not')
	effs.append(isnt_fin_eff)
	# del act
	act_argslist = pddl.TypedArgList([])
	act_subformulas = [pddl.Predicate('act', act_argslist)]
	act_eff = pddl.Formula(act_subformulas, 'not')
	effs.append(act_eff)
	if print_condition:
		print '\ncomposed the following effects to action end-',name,'-f'
		for eff in effs:
			print ' ', eff.asPDDL()
	return effs;

def MakeActions_end_f(dom, prob, params):
	''' get agent list e.g [person1, person2]
		dom is pddl.Domain
		prob is pddl.Problem
		returns end_f_actions as list of actions
	'''
	agentslist = params.agentslist
	print_condition = params.print_condition
	if print_condition: print '\nMaking end_f actions:'
	end_f_actions = []
	i = 0
	for name in agentslist:
		agent_goals = GrabGoals(prob, name, params)
		for inverse_goal in agent_goals:
			i += 1
			action_name = 'end-' + name + '-' + inverse_goal.name +'-f-'+ str(i)
			parameters = pddl.TypedArgList([])
			pre = MakeConds_end_f(prob, name, inverse_goal, params)
			effs = MakeEffs_end_f(name, print_condition)
			end_f = pddl.Action(action_name, parameters, pre, effs)
			end_f_actions.append(deepcopy(end_f))
	if print_condition:
		print '\ncomposed ', len(end_f_actions), ' end_s actions as following:'
		for i in range(len(end_f_actions)):
			print '\nthe (', i+1 ,') action is: \n', end_f_actions[i].asPDDL()
	return end_f_actions;

def MakeDomain(dom, prob, params):
	agentTypename = params.agentTypename
	waitlist = params.waitlist
	fixADL  = params.fixADL
	print_condition  = params.print_condition
	name = 'c' + dom.name
	if print_condition:
		print ' the name of the new domain is:\n  ', name
	reqs = MakeReqs(dom, prob)
	if print_condition:
		print ' the requirements are:\n  ', reqs
	types = MakeTypes(dom, prob)
	if print_condition:
		print ' the types are:\n  ', types.asPDDL()
	constants = MakeConstants(dom, prob)
	if print_condition:
		print ' the constants are:\n  ', constants.asPDDL()
	predicates = MakePredicates(dom, prob, params)
	if print_condition:
		print ' the predicates are:\n',
		for pred in predicates:
			print '  ', pred.asPDDL()
	functions = MakeFunctions(dom, prob, params)
	if print_condition:
		print ' the functions are:\n',
		for func in functions:
			print '  ', func.asPDDL()
	actions = []
	actions = actions + MakeActions_end_s(dom, prob, params) + \
			  MakeActions_end_f(dom, prob, params)
	if print_condition:
		print ' the actions are:\n',
		for act in actions:
			print '  ', act.name
	durative_actions = []
	for dact in dom.durative_actions: # a_s
		durative_actions.append(MakeActions_s(dact, constants, params))
	# a_f_start = []
	for dact in dom.durative_actions: # a_f_start
		durative_actions += MakeActions_fstart(dact, constants, params)
	for dact in dom.durative_actions: # a_f_end
		durative_actions += MakeActions_fend(dact, constants, params)
	for dact in dom.durative_actions: # a_finv_start
		durative_actions.append(MakeAction_finv_start(dact, constants, params))
	for dact in dom.durative_actions: # a_finv_end
		durative_actions.append(MakeAction_finv_end(dact, constants, params))
	for dact in dom.durative_actions: # a_wait
		durative_actions += MakeActions_Wait(dact, constants, params)
	durative_actions = filter(None, durative_actions)
	if fixADL:
		if print_condition:
			print '\nremove ADL from durative_actions conditions...'
		for i in range(len(durative_actions)):
			durative_actions[i].cond = FixADLConds(durative_actions[i].cond)
		if print_condition:
			print 'ADL is removed from durative_actions conditions.\n'
	if print_condition:
		print ' the durative actions are:\n', map(lambda x: str(x.name) , durative_actions)
	c_domain = pddl.Domain(name, reqs, types, constants, predicates, functions, actions, durative_actions)
	return c_domain;

def MakeInitialState_old(dom, prob, constants, params):
	agentslist = params.agentslist
	waitlist = params.waitlist
	print_condition = params.print_condition
	initial_state = []
	# act as a formula
	act = pddl.Formula([pddl.Predicate('act', pddl.TypedArgList([]))], None)
	initial_state.append(act)
	# {isnt-fin for all agents}
	for agent in agentslist:
		arg = pddl.TypedArg(agent)
		form = pddl.Formula([pddl.Predicate('isnt-fin', pddl.TypedArgList([arg]))], None)
		initial_state.append(form)
	# {f_i V f e initial state}
	for f in prob.initialstate:
		for agent in agentslist:
			f_local = deepcopy(f)
			f_local.subformulas[0].name += '-l'
			f_local.subformulas[0].args.args.insert(0, pddl.TypedArg(agent))
			initial_state.append(f_local)
	# {f_g V f e initial state}
	for f in prob.initialstate:
		f_global = deepcopy(f)
		f_global.subformulas[0].name += '-g'
		initial_state.append(f_global)
	# {f_inv = 0 V f e F}
	invs_forms = []
	consts_list = []
	for arg in constants.args:
		consts_list.append([arg.arg_name, arg.arg_type])
	preds = deepcopy(dom.predicates)
	for pred in preds:
		form_args = map(lambda x: x.arg_type, pred.args.args)
		options = []
		for i in range(len(form_args)):
			possible_args = [item[0] for item in consts_list if item[1] == form_args[i]]
			options.append(possible_args)
		combinations = itertools.product(*options)
		for comb in combinations:
			f_name = pred.name + '-inv'
			arglist = pddl.TypedArgList([pddl.TypedArg(c) for c in comb])
			normal_form = pddl.Formula([pddl.Predicate(f_name, arglist)])
			inv_form_name = '= ' + normal_form.asPDDL() + ' 0'
			inv_form = pddl.Formula([pddl.Predicate(inv_form_name, pddl.TypedArgList([]))])
			invs_forms.append(inv_form)
	initial_state += invs_forms
	# not(f_wait)
	wait_forms = []
	wait_preds = []
	for waitpred in waitlist:
		print '\nwaitpred is: ' ,waitpred
		for pred in dom.predicates:
			if waitpred == pred.name:
				print 'pred name is: ', pred.name,'!!!!!'
				temp = deepcopy(pred)
				temp.name = temp.name + '-not-wt'
				temp.args.args.insert(0, pddl.TypedArg(params.agentTypeparameter, params.agentTypename))
				wait_preds.append(temp) # get relevant preds
	print 'the len of wait_preds is: ', len(wait_preds)
	for pred in wait_preds:
		form_args = map(lambda x: x.arg_type, pred.args.args)
		print 'form args is: ', form_args
		options = []
		for i in range(len(form_args)):
			possible_args = [item[0] for item in consts_list if item[1] == form_args[i]]
			print 'possible_args is: ', possible_args
			options.append(possible_args)
		print 'options are: ', options
		combinations = itertools.product(*options)
		print 'combinations are: ', combinations
		for comb in combinations:
			print 'TESSSTTTTTTTT'
			form_name = pred.name
			print 'the form name is: ', form_name, '!!!!!!!!!!!!!!!!'
			form_arglist = pddl.TypedArgList([pddl.TypedArg(c) for c in comb])
			form = pddl.Formula([pddl.Predicate(form_name, form_arglist)])
			initial_state.append(deepcopy(form))
	if print_condition:
		print '\nThe initial state is:'
		for f in initial_state:
			print f.asPDDL()
	return initial_state;

def MakeInitialState(dom, prob, constants, params):
	agentslist = params.agentslist
	waitlist = params.waitlist
	print_condition = params.print_condition
	initial_state = []
	# act as a formula
	act = pddl.Formula([pddl.Predicate('act', pddl.TypedArgList([]))], None)
	initial_state.append(act)
	# {isnt-fin for all agents}
	for agent in agentslist:
		arg = pddl.TypedArg(agent)
		form = pddl.Formula([pddl.Predicate('isnt-fin', pddl.TypedArgList([arg]))], None)
		initial_state.append(form)
	# {f_i V f e initial state}
	for f in prob.initialstate:
		for agent in agentslist:
			f_local = deepcopy(f)
			f_local.subformulas[0].name += '-l'
			f_local.subformulas[0].args.args.insert(0, pddl.TypedArg(agent))
			initial_state.append(f_local)
	# {f_g V f e initial state}
	for f in prob.initialstate:
		f_global = deepcopy(f)
		f_global.subformulas[0].name += '-g'
		initial_state.append(f_global)
	# {f_inv = 0 V f e F}
	invs_forms = []
	preds = deepcopy(dom.predicates)
	for pred in preds:
		# print '\n',pred.asPDDL()
		argOptions = []
		for arg in pred.args.args:
			argOptions.append(getObjectsOfType(dom, prob, arg.arg_type, params))
		# print argOptions
		allArgOptions = itertools.product(*argOptions)
		# print [a for a in allArgOptions]
		for args in allArgOptions:
			f_name = pred.name + '-inv'
			arglist = pddl.TypedArgList([pddl.TypedArg(c) for c in args])
			normal_form = pddl.Formula([pddl.Predicate(f_name, arglist)])
			inv_form_name = '= ' + normal_form.asPDDL() + ' 0'
			inv_form = pddl.Formula([pddl.Predicate(inv_form_name, pddl.TypedArgList([]))])
			invs_forms.append(inv_form)
	# for form in invs_forms:
	# 	print form.asPDDL()
	initial_state += invs_forms
	# not(f_wait)
	wait_forms = []
	for pred in dom.predicates:
		if not pred.name in waitlist:
			continue
		# print pred.name , ' in wait list'
		tempPred = deepcopy(pred)
		tempPred.name = tempPred.name + '-not-wt'
		tempPred.args.args.insert(0, pddl.TypedArg('?'+params.agentTypeparameter, params.agentTypename))
		argOptions = []
		for arg in tempPred.args.args:
			argOptions.append(getObjectsOfType(dom, prob, arg.arg_type, params))
		allArgOptions = itertools.product(*argOptions)
		for args in allArgOptions:
			form_name = tempPred.name
			arglist = pddl.TypedArgList([pddl.TypedArg(c) for c in args])
			form = pddl.Formula([pddl.Predicate(form_name, arglist)])
			wait_forms.append(form)
	initial_state +=wait_forms
	if print_condition:
		print '\nThe initial state is ', len(initial_state),' long.'
		for f in initial_state:
			print f.asPDDL()
	return initial_state;

def MakeGoalState(dom, prob, params):
	agentslist = params.agentslist
	print_condition = params.print_condition
	subformulas = [] # list of formulas
	# {failure}
	fail_pred = pddl.Predicate(u'failure', pddl.TypedArgList([]))
	fail_form = pddl.Formula([fail_pred])
	subformulas.append(fail_form)
	# fin_i
	for agent in agentslist:
		fin_args = pddl.TypedArgList([pddl.TypedArg(agent)])
		fin_pred = pddl.Predicate(u'fin', fin_args)
		subformulas.append(fin_pred)
	goal_state = pddl.Formula(subformulas, 'and')
	if print_condition:
		print '\nthe goals are:'
		print goal_state.asPDDL()
	return goal_state

def getObjectsOfType(dom, prob, objType, params = None):
	listOftypes = []
	listOfobjects = []
	listOftypes.append(objType)
	for typeArg in dom.types.args:
		if typeArg.arg_type == objType:
			listOftypes.append(typeArg.arg_name)
	for typeArg in dom.types.args:
		if typeArg.arg_type in listOftypes:
			listOftypes.append(typeArg.arg_name)
	listOftypes = list(set(listOftypes))
	constants = MakeConstants(dom, prob)
	for objArg in constants.args:
		if objArg.arg_type in listOftypes:
			listOfobjects.append(objArg.arg_name)
	if not params == None :
		if params.print_condition:
			print 'the objType is: ', objType
			print 'listOftypes is: ', listOftypes
			print 'listOfobjects is: ', listOfobjects
	return listOfobjects

def MakeProblem(dom, prob, params):
	#     def __init__(self, name, domainname, objects, initialstate, goal, metric=None):
	agentslist = params.agentslist
	waitlist = params.waitlist
	print_condition = params.print_condition
	name = 'c' + prob.name
	domainname = 'c' + dom.name
	objects = pddl.TypedArgList([])
	constants = MakeConstants(dom, prob)
	initialstate = MakeInitialState(dom, prob, constants, params)
	goal = MakeGoalState(dom, prob, params)
	c_problem = pddl.Problem(name, domainname, objects, initialstate, goal)
	if print_condition:
		print 'the problem name is: ', name
		print 'the domain name is: ', domainname
		print 'the objects are: ', objects.asPDDL()
		print 'the initial state is: '
		for f in initialstate:
			print '  ' , f.asPDDL()
		print 'the goal state is:\n  ', goal.asPDDL()
		print '\nthe problem is:\n', c_problem.asPDDL()
	return c_problem

if __name__ == "__main__":
	print '\n'*100
	parse = True
	get_agents = True
	make_preds = False
	make_funcs = False
	make_consts = False
	make_action_s = False
	make_action_fstart = False
	make_action_fend = False
	make_action_finv_start = False
	make_action_finv_end = False
	make_action_wx = False
	make_action_end_s = False
	make_action_end_f = False
	grab_goals = False
	make_initial_state = False
	make_goal_state = False
	make_compiled_domain = False
	make_compiled_problem = False
	make_files = False
	print_condition = True
	FixADL = False

	loadDrink = False
	loadDriver = True

	if loadDrink:
		print 'drink problem is loaded.'
		waitlist = ['on-table']
		agentslist = ['person1', 'person2']
		agentTypename = 'agent'
		domain_path = '../expfiles/drink/drink-world3.pddl'
		problem_path = '../expfiles/drink/drink-prob3.pddl'
		
	elif loadDriver:
		print 'driver problem is loaded'
		waitlist = []
		agentslist = ['d0', 'd1']
		agentTypename = 'driver'
		domain_path =  '../expfiles/driverlog/domain.pddl'
		problem_path = '../expfiles/driverlog/pfile1.pddl'
	else:
		print 'no problem is loaded ...'
		exit()



	if parse:
		(dom,prob) = pddl.parseDomainAndProblem(domain_path, problem_path)
	if get_agents:
		print 'get_agents is True'
		constants = MakeConstants(dom, prob)
		agents = GetAgents(constants, params)

	if make_preds:
		preds = MakePredicates(dom, prob, params)
	if make_funcs:
		funcs = MakeFunctions(dom, prob, params)
	if make_consts:
		constants = MakeConstants(dom, prob)
	if make_action_fstart:
		action = dom.durative_actions[1]
		if print_condition:
			print '\nthe action is: ', action.name
		actions_fstart = MakeActions_fstart(action, constants, params)
		if fixADL:
			for action in actions_fstart:
				action.cond = FixADLConds(action.cond)
				if print_condition:
					print '\nthe new fixed conditions are:'
					for cond in action.cond:
						print ' ',cond.asPDDL()
	if make_action_fend:
		action = dom.durative_actions[2]
		if print_condition:
			print '\nthe action is: ', action.name
		actions_fend = MakeActions_fend(action, constants, params)
		if fixADL:
			for action in actions_fend:
				action.cond = FixADLConds(action.cond)
			if print_condition:
				print '\nthe new fixed conditions are:'
				for cond in action.cond:
					print ' ',cond.asPDDL()
	if make_action_s:
		action = dom.durative_actions[0]
		constants = MakeConstants(dom, prob)
		action_s = MakeActions_s(action, constants, waitlist, agentTypename, print_condition = True)
	if make_action_finv_start:
		action = dom.durative_actions[0]
		actions_finv_start = MakeAction_finv_start(action, constants, params)
	if make_action_finv_end:
		action = dom.durative_actions[1]
		actions_finv_end = MakeAction_finv_end(action, constants, params)
	if make_action_wx:
		print '\n'*5
		action = dom.durative_actions[0]
		actions_wait = MakeActions_Wait(action, constants, params)
	if make_action_end_s:
		end_s_actions = MakeActions_end_s(dom, prob, params)
	if make_action_end_f:
		print '\n'*50
		end_f_actions = MakeActions_end_f(dom, prob, params)
	if grab_goals:
		goals = GrabGoals(prob, 'person2', params)
	if make_initial_state:
		print '\nBuilding initial state ...'
		constants = MakeConstants(dom, prob)
		initial_state = MakeInitialState(dom, prob, constants, params)
	if make_goal_state:
		print '\nBuilding goal state ...'
		goal_state = MakeGoalState(dom, prob, params)
	if make_compiled_domain:
		print '\n'*2
		print 'Parsing domain ...'
		(dom,prob) = pddl.parseDomainAndProblem(domain_path, problem_path)
		print 'Parsing domain and problem complete.\n'
		print 'Compiling new domain ...\n'
		c_domain = MakeDomain(dom, prob, params)
		if make_files:
			c_domain_file = open('c_domain_file_tmp.pddl','wb')
			c_domain_file.write(c_domain.asPDDL())
			c_domain_file.close()
	if make_compiled_problem:
		print '\n'*2
		print 'Parsing problem ...'
		(dom,prob) = pddl.parseDomainAndProblem(domain_path, problem_path)
		print 'Parsing domain and problem complete.\n'
		c_problem = MakeProblem(dom, prob, params)
		if make_files:
			c_problem_file = open('c_problem_file_tmp.pddl','wb')
			c_problem_file.write(c_problem.asPDDL())
			c_problem_file.close()
