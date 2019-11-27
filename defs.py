#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
    Created on Fri Aug  9 10:13:41 2019
    Common definitions, directories, other constants.
'''

import os

# The filenames of the 11 assignments:
assignments = ['Circuit_1.v', 'Circuit_2.v', 'UDP_Majority_4.v',
               'AdderSub.v', 'Compare.v', 'DecimalAdder.v',
               'OddFunction.v', 'FiniteStateMachine.v', 'StateDiagram.v',
               'SerialComplementer.v', 'Counter_1.v',
               ]

# Students are numbered from 002 to 114 inclusive:
students = ['%03d' % d for d in range(2, 115)]

# format of JW's filename:
#   Anon-XXX-submit-YYYY-MM-DD-HH-MM-SS-NN..NNN.txt

# Used by JW to separate filename elements:  Anon-005-submit-2019-04- etc.
FILENAME_SEP = '-'

# Kinds of query (and thus thrid field of filenames):
MULTICHOICE = 'multichoice'
SUBMIT = 'submit'
SHOWRESULTS = 'showresults'

VERILOG_SUFFIX = '.v'
JW_FILE_SUFFIX = '.txt'

# Where the data files live:
_THIS_DIR = os.path.dirname(__file__)
DATAROOT = os.path.join(_THIS_DIR, '..', 'anonymiseddata')

SPECIAL_CIRC = 'CIRC'
SPECIAL_INST = 'INST'

special_src = {
        SPECIAL_CIRC: os.path.join(_THIS_DIR, '..', 'classrepdistributed'),
        SPECIAL_INST: os.path.join(_THIS_DIR, '..', 'johnnyscode')
    }


ALL_SPECIALS = [SPECIAL_CIRC, SPECIAL_INST]
ALL_METRICS = ['jaccard', 'tversky', 'sequence']
ALL_PROCESS = ['orig', 'clean', 'token']

# File suffix for any data I write:
DATA_SUFFIX = '.dat'
DOT_SUFFIX = '.dot'


RESULTS_DIR = os.path.join(_THIS_DIR, '..', 'results')

GRAPHS_DIR = os.path.join(RESULTS_DIR, 'graphs')
GRAPHS_SUFFIX = '.pdf'
GRAPH_LABEL_SIZE = 16


def latest_dir(proc='token'):
    '''Where the latest vesion of each project is stored'''
    return os.path.join(RESULTS_DIR, 'latest' + FILENAME_SEP + proc)


def special_dir(proc='token'):
    '''Where the special (circ/inst) versions are stored'''
    return os.path.join(RESULTS_DIR, 'special' + FILENAME_SEP + proc)


def special_filename(metric, proc):
    '''Return the full filepath of the special similiariy file'''
    basename = FILENAME_SEP.join(['special', metric, proc])
    return os.path.join(RESULTS_DIR, basename+DATA_SUFFIX)


def did_assignment(proc='token'):
    '''
        Find out how many students attempted each assignment.
        Return a dict mapping assignment to number of students.
    '''
    da = {}
    vdir = latest_dir(proc)
    _, _, files = next(os.walk(vdir))
    for assign in assignments:
        attempt_count = len([f for f in files if f.endswith(assign)])
        da[assign] = attempt_count
    return da
