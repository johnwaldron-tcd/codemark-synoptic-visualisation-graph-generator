#!/usr/bin/python3
'''
    Look for cliques based on the similiairy metrics.
    Canm produce a list of cliques or a dot graph.
    (Here clique = partition, all students with same sim betwen them).
'''

import os
import numpy as np

import matplotlib.pyplot as plt

from graphviz import Graph

import defs
# Make sure we only use Type 1 fonts:
plt.rc('text', usetex=True)
plt.rc('font', family='serif')


def read_assignment_threshold(basename, threshold):
    '''
        Read the similarity data from one file and group by assignment.
        Return two dicts, each indexed by assignments.
        For each assignment, give
            over: a list of pairs with sim >= threshold
            under: a mapping from pairs to sim value, when sim < threshold
    '''
    simfile = os.path.join(defs.RESULTS_DIR, basename+defs.DATA_SUFFIX)
    over = {a: [] for a in defs.assignments}
    under = {a: {} for a in defs.assignments}
    with open(simfile, 'r') as fh:
        for line in fh:
            s1, a1, s2, a2, sim = line.strip().replace('-', ' ').split()
            sim = int(sim)
            # Comparison within one project between different students
            if a1 == a2 and s1 != s2:
                if sim >= threshold:
                    over[a1].append((s1, s2))
                else:
                    under[a1][(s1, s2)] = sim
    return (over, under)


def read_special_threshold(basename, pairs, threshold):
    '''
        Read the similarity data from one 'special' file and
        add any sims *over* the threshold to the existing dict of pairs.
        This pairs dict is indexed by assignment name.
    '''
    basename = 'special' + defs.FILENAME_SEP + basename
    simfile = os.path.join(defs.RESULTS_DIR, basename+defs.DATA_SUFFIX)
    with open(simfile, 'r') as fh:
        for line in fh:
            skind, p1, stu, p2, sim = line.strip().replace('-', ' ').split()
            sim = int(sim)
            if p1 == p2 and sim >= threshold:
                pairs[p1].append((skind, stu))
    # No return, as pairs has been updared.


def make_cliques(pairlist):
    '''
        Given a list of pairs that are related, partition the elements.
        Return a list of cliques, ie elements related by transitive closure.
        Cliques are sorted by size (biggest first).
    '''
    cliques = []
    for (s1, s2) in pairlist:
        # First find out which (if any) cliques s1 and s2 are in already:
        s1c, s2c = -1, -1
        for i, c in enumerate(cliques):
            if s1 in c:
                s1c = i
            if s2 in c:
                s2c = i
        # Now make sure they're put in the *same* clique:
        if s1c == -1 and s2c == -1:   # Neither in a clique, make new one
            cliques.append([s1, s2])
        elif s1c >= 0 and s2c == -1:  # Add s2 to s1's clique
            cliques[s1c].append(s2)
        elif s1c == -1 and s2c >= 0:  # Add s1 to s2's clique
            cliques[s2c].append(s1)
        elif s1c != s2c:  # Already in different cliques, must merge these
            cliques[s1c].extend(cliques[s2c])
            del cliques[s2c]
    # Sort the cliques by size, largest first:
    return sorted(cliques, key=lambda c: len(c), reverse=True)


def get_cliques(metric, proc, threshold, read_special=True):
    '''
        Read data from file, make cliques, return cliques and others.
        - over: cliques (sim was >=threshold), indexed by assignments
        - under: pairs to sim (<threshold), indexed by assignments
    '''
    basename = metric + defs.FILENAME_SEP + proc
    (pairs, under) = read_assignment_threshold(basename, threshold)
    if read_special:
        read_special_threshold(basename, pairs, threshold)
    over = {assign: make_cliques(pairs[assign]) for assign in defs.assignments}
    return (over, under)


def print_cliques(over, outfh):
    '''
        For each assignment, list all its cliques and their members.
    '''
    for assign in defs.assignments:
        print('#', assign, file=outfh)
        for c in over[assign]:
            print('\t', len(c), c, file=outfh)
        print('', file=outfh)


def print_all_cliques(metric, threshold):
    '''
        Write all the cliques for each processing type (orig/clean/token)
        to a single file for this metric/threshold value.
    '''
    filename = defs.FILENAME_SEP.join(['clique', metric, str(threshold)])
    outfile = os.path.join(defs.RESULTS_DIR, filename+defs.DATA_SUFFIX)
    with open(outfile, 'w') as fh:
        for proc in defs.ALL_PROCESS:
            print('##### Metric = {}, process={}, threshold={} #####'
                  .format(metric, proc, threshold), file=fh)
            over, _ = get_cliques(metric, proc, threshold)
            print_cliques(over, fh)
            print('', file=fh)
            print('', file=fh)
    print('Cliques written to {}'.format(filename))


def who_did_what():
    '''
        Find out which students did each assignment.
        Do this by looking for a 'latest' file with the right name.
        Return a dict mapping student to list of 0/1 per assignment.
    '''
    vdir = defs.latest_dir()
    students = {s: [0]*len(defs.assignments) for s in defs.students}
    for stu, did in students.items():
        for anum, assign in enumerate(defs.assignments):
            fpath = os.path.join(vdir, defs.FILENAME_SEP.join([stu, assign]))
            if os.path.isfile(fpath):
                students[stu][anum] = 1  # Student did this assignment
    return students


def dotgraph_cliques(over, under, plot_assignment, colors=[]):
    '''
        Produce a dot graph where the nodes are the cliques,
        and the edges represent sim value between cliques.
        We write one dot graph for each assignment.
    '''
    for assign in plot_assignment:
        basename = assign.replace(defs.VERILOG_SUFFIX, '')
        outfile = os.path.join(defs.GRAPHS_DIR, basename+defs.DOT_SUFFIX)
        dot = Graph(comment=basename, filename=outfile)
        dot.attr('node', fontsize='20')
        # Each clique is a single node in the graph:
        for i, c in enumerate(over[assign]):
            size = len(c)
            nodeargs = {'label': '{}'.format(size),
                        'height': '{}'.format(size/10),
                        'width': '{}'.format(size/10)}
            if len(colors) > 0:  # Then use the given colour:
                nodeargs['style'] = 'filled'
                nodeargs['fillcolor'] = colors[i]
            # Else just colour the node with the CIRC version red:
            elif defs.SPECIAL_CIRC in c:
                nodeargs['style'] = 'filled'
                nodeargs['fillcolor'] = 'red'
            dot.node('n{}'.format(i), **nodeargs)
            # Now put an edge to all the other nodes:
            my_rep = c[0]  # Use first element as clique representative
            for j in range(i+1, len(over[assign])):
                ur_rep = over[assign][j][0]
                if (my_rep, ur_rep) in under[assign]:
                    sim = under[assign][(my_rep, ur_rep)]
                    dot.edge('n{}'.format(i), 'n{}'.format(j),
                             label='{}%'.format(sim))
        dot.render()


def get_barchart_values(over):
    '''
        Get the numbers in each clique on a per-assignment basis.
        The sizes are returned in a list, last element is no attempt,
        second-last element is number of cliques of size 1.
        Sort the others based on clique size.
        Also return the max number of cliques for any assignment.
    '''
    attempts = defs.did_assignment()
    tot_students = len(defs.students)
    mybars = {}
    for assign, cliques in over.items():
        mybars[assign] = [len(c) for c in cliques]
    maxcliques = max([len(c) for c in mybars.values()])
    for assign, csizes in mybars.items():
        # Make all the same size (maxcliques) - pad with 0s:
        csizes.extend([0] * (maxcliques - len(csizes)))
        # A count for the students who did this on their own:
        csizes.append(attempts[assign] - sum(csizes))
        # A count for students who did not attempt this:
        csizes.append(tot_students - sum(csizes))
    return maxcliques+2, mybars


def barchart_cliques(over, save_to_file=False):
    '''
        Plot a stacked barchart showing the clique sizes,
        one stacked bar per assignment, one bar section per clique.
    '''
    fig, ax = plt.subplots(nrows=1,
                           ncols=1,
                           figsize=(10, 10), sharey=True)
    parts_in_bar, barvals = get_barchart_values(over)

    def one_bar(col, last_bar, **kwargs):
        ''' Plot a single stacked bar in the barchart '''
        horiz = np.array([barvals[assign][col] for assign in defs.assignments])
        num_bars = len(barvals)
        width = 0.5
        plt.bar(range(num_bars), horiz, width, bottom=last_bar, **kwargs)
        return horiz

    last_horiz = np.zeros(len(defs.assignments))
    for i in range(parts_in_bar-2):
        last_horiz += one_bar(i, last_horiz, edgecolor='gray')
    # Now plot the no-shows, but color=white
    last_horiz += one_bar(-1, last_horiz, color='white')
    last_horiz += one_bar(-2, last_horiz, color='gold', edgecolor='gray')
    # set style for the axes
    ax.set_xticks(range(1+len(defs.assignments)))
    ax.set_xticklabels([p.replace('.v', '').replace('_', '\\_')
                        for p in defs.assignments], rotation=45)
    ax.set_ylabel('No of students')
    ax.set_ylim(0, len(defs.students))
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)
    if save_to_file:
        basename = 'barchart'
        outfile = os.path.join(defs.GRAPHS_DIR, basename + defs.GRAPHS_SUFFIX)
        plt.savefig(outfile, bbox_inches='tight')
    else:
        plt.show()
    return plt.rcParams['axes.prop_cycle'].by_key()['color'].copy()


def count_buddies(over):
    '''
        For each student, work out how many people they've a sim with.
        Print a report, one line per student.
        Return a dict mapping students to list of sim counts per assignment.
    '''
    buddies = who_did_what()
    buddies[defs.SPECIAL_CIRC] = [0]*len(defs.assignments)
    buddies[defs.SPECIAL_INST] = [1]*len(defs.assignments)
    for anum, clist in enumerate(over.values()):
        for clique in clist:
            for stu in clique:
                if stu in buddies:
                    buddies[stu][anum] = len(clique)  # no. of buddies
    # Sort the students based on number of buddies (most first):
    sortstu = sorted(buddies.keys(),
                     key=lambda s: sum(buddies[s]), reverse=True)
    for s in sortstu:
        # Number of assignments where buddies is >1:
        acount = len([1 for b in buddies[s] if b > 1])
        # Total number of buddies over all assignments:
        btotal = sum(buddies[s])
        print('{:4s} {:2d} {:3d} {}'.format(s, acount, btotal, buddies[s]))
    return buddies


function = 3
if __name__ == '__main__':
    if function == 1:
        for threshold in [100]:
            print_all_cliques('jaccard', threshold)
    elif function == 2:
        (over, under) = get_cliques('jaccard', 'token', 100)
        dotgraph_cliques(over, under, defs.assignments)
    elif function == 3:
        over, under = get_cliques('jaccard', 'token', 100)
        colors = barchart_cliques(over, True)
        dotgraph_cliques(over, under, ['DecimalAdder.v'], colors)
    elif function == 4:
        over, _ = get_cliques('jaccard', 'token', 100)
        count_buddies(over)
