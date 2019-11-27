#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
    Created on Fri Aug  9 10:13:41 2019
    Plot graphs for the codecompare paper.
'''

import os

import numpy as np
import matplotlib.pyplot as plt

import defs

# Make sure we only use Type 1 fonts:
plt.rc('text', usetex=True)
plt.rc('font', family='serif')
plt.rc('axes', labelsize=defs.GRAPH_LABEL_SIZE)


def read_assignment_sim_all(basename):
    '''
        Read the similarity data from one file and group by assignment.
        So return a dict, mapping assignment to list of sim values,
        for all students doing that assignment (vs all other students).
    '''
    inpath = os.path.join(defs.RESULTS_DIR, basename+defs.DATA_SUFFIX)
    sims = {a: [] for a in defs.assignments}
    with open(inpath, 'r') as fh:
        for line in fh:
            s1, a1, s2, a2, sim = line.strip().replace('-', ' ').split()
            if a1 == a2 and s1 != s2:  # Comparison within one project
                sims[a1].append(int(sim))
    return sims


def read_assignment_sim_max(basename):
    '''
        Read the similarity data from one file and group by assignment.
        We want the max sim values for each student.
        Return a dict, mapping assignment to list of (max) sim values.
   '''
    inpath = os.path.join(defs.RESULTS_DIR, basename+defs.DATA_SUFFIX)
    sims = {a: {} for a in defs.assignments}
    with open(inpath, 'r') as fh:
        for line in fh:
            s1, a1, s2, a2, sim = line.strip().replace('-', ' ').split()
            if a1 == a2 and s1 != s2:  # Comparison within one project
                if s1 not in sims[a1]:
                    sims[a1][s1] = -1
                sims[a1][s1] = max(sims[a1][s1], int(sim))
    return {a: list(sims[a].values()) for a in defs.assignments}


# #####################################################################
# Violin Plots
# #####################################################################


def _adjacent_values(vals, q1, q3):
    '''Outliers: return the bounds for +/- 1.5 times the IQR'''
    upper_adjacent_value = q3 + (q3 - q1) * 1.5
    upper_adjacent_value = np.clip(upper_adjacent_value, q3, vals[-1])
    lower_adjacent_value = q1 - (q3 - q1) * 1.5
    lower_adjacent_value = np.clip(lower_adjacent_value, vals[0], q1)
    return lower_adjacent_value, upper_adjacent_value


def plot_one_violin(ax, sims, metric, proc):
    '''
        Violin plots showing similarities for each project.
        For each violin, show dot for median, bar for the IQR (Q1 to Q3),
        and whiskers for 1.5*IQR.
    '''
    data = [sims[a] for a in defs.assignments]
    parts = ax.violinplot(data, showmeans=False, showmedians=False,
                          showextrema=False)
    # Set the colours for the violin plots:
    for pc in parts['bodies']:
        pc.set_facecolor('#4f90d9')
        pc.set_edgecolor('black')
        pc.set_alpha(1)
    # Do the quartiles:
    triples = [np.percentile(d, [25, 50, 75]) for d in data]
    quartile1, medians, quartile3 = [t for t in zip(*triples)]
    # Print quartile data to screen, just for confirmation
    whiskers = np.array([
        _adjacent_values(sorted_array, q1, q3)
        for sorted_array, q1, q3 in zip(data, quartile1, quartile3)])
    whiskersMin, whiskersMax = whiskers[:, 0], whiskers[:, 1]
    # Now draw the median, IQR and whiskers:
    inds = np.arange(1, len(medians) + 1)
    ax.scatter(inds, medians, marker='o', color='white', s=30, zorder=3)
    ax.vlines(inds, quartile1, quartile3, color='k', linestyle='-', lw=5)
    ax.vlines(inds, whiskersMin, whiskersMax, color='k', linestyle='-', lw=1)

    # set style for the axes
    ax.set_title('Version = \\textbf{{{}}}, '.format(proc) +
                 'similiarity method = \\textbf{{{}}}'.format(metric))
    ax.set_xlabel('Assignments')
    ax.set_xticks(range(1, 1+len(defs.assignments)))
#    ax.set_xticklabels([''] + [p.replace('.v', '').replace('_', '\\_')
#                               for p in defs.assignments], rotation=45) 
    ax.set_ylabel('Percentage similarity')
    ax.set_ylim(0, 100)
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)


def plot_assignment_sims(versus_all, save_to_file):
    '''
        Plot all the violin plots (all metrics/prcoesses) in a single figure.
        Each subfigure has a violin plot for each assignment.
        Can do all sims per assignment, or just the max sim for each student.
    '''
    fig, ax = plt.subplots(nrows=len(defs.ALL_METRICS),
                           ncols=len(defs.ALL_PROCESS),
                           figsize=(20, 15), sharey=True)
    #fig.tight_layout()
    plt.subplots_adjust(hspace=0.3)
    plt.rc('axes', labelsize=defs.GRAPH_LABEL_SIZE)
    for i, metric in enumerate(defs.ALL_METRICS):
        for j, proc in enumerate(defs.ALL_PROCESS):
            basename = metric + defs.FILENAME_SEP + proc
            if versus_all:
                sims = read_assignment_sim_all(basename)
            else:  # Only want max sim value for each student:
                sims = read_assignment_sim_max(basename)
            plot_one_violin(ax[i][j], sims, metric, proc)
    if save_to_file:
        #fig.set_size_inches(12, 6, forward=True)
        basename = defs.FILENAME_SEP.join(['violin',
                                           'all' if versus_all else 'max'])
        outfile = os.path.join(defs.GRAPHS_DIR, basename + defs.GRAPHS_SUFFIX)
        plt.savefig(outfile, bbox_inches='tight', pad_inches=0)
        print(' Violin plots written to {}'.format(basename))
    else:
        plt.show()


# #####################################################################
# Silhouette Code
# #####################################################################

def read_diff_totals(basename, pnum):
    '''
        Read the similarity data from one file and group by point & cluster.
        Here we assume: point=(assignment, student) and cluster=assignment.
        For each (assignment, student), collect the total diffs per cluster.
        Return an map of the difference totals, this looks like
            (assignment, student) -> list-of-diffs-per-assignment
    '''
    # Prepare map to hold diff totals per cluster:
    totals = {a: {} for a in defs.assignments}
    # Now read in the data and fill up the totals array:
    inpath = os.path.join(defs.RESULTS_DIR, basename+defs.DATA_SUFFIX)
    with open(inpath, 'r') as fh:
        for line in fh:
            s1, a1, s2, a2, sim = line.strip().replace('-', ' ').split()
            if s1 == s2:  # always ignore self-self comparison
                continue
            if s1 not in totals[a1]:
                totals[a1][s1] = [0] * len(defs.assignments)
            # File has percent similiarity, we want difference, so:
            diff = 100 - int(sim)
            totals[a1][s1][pnum[a2]] += diff
    return totals


def calc_assignment_silhouette(totals, pnum):
    '''
        Calculate the silhouette value for each point=(assignment, student).
        Given totals, mapping assign x student x assign -> diff
        See: https://en.wikipedia.org/wiki/Silhouette_(clustering)
        Return the values in an np.array, shape = #assignments, #students
    '''
    attempts = defs.did_assignment()
    silhouette = {p: {} for p in defs.assignments}
    for a in defs.assignments:
        for s in defs.students:
            if s not in totals[a]:  # student didn't do this assignment
                continue
            oth_totals = totals[a][s].copy()
            #  a(i) value is the average for a's cluster:
            own_total = oth_totals.pop(pnum[a])
            own_average = own_total / (attempts[a] - 1)
            # b(i) value is min average for all other clusters:
            oth_average = min([t/attempts[a] for t in oth_totals])
            # s(i) = (b(i) - a(i)) / max((a(i), b(i)))
            silhouette[a][s] = ((oth_average - own_average)
                                / max(own_average, oth_average))
    return silhouette


def print_silhouette(silhouette):
    '''
        Print the silhouette value for each (assignment, student) point
        and then print the average silhouette value for each assignment.
    '''
    cluster_sil = {a: 0 for a in defs.assignments}
    for a in defs.assignments:
        print()
        for s in defs.students:
            if s in silhouette[a]:
                print('\t', a, s, '%.2f' % silhouette[a][s])
        pavg = sum(silhouette[a].values()) / len(silhouette[a].values())
        print('=== Average for cluster {}: {:+.2f}'.format(a, pavg))
    print(cluster_sil)


def calc_silhouette():
    # Number the assignments and students:
    num_assignments = len(defs.assignments)
    pnum = dict(zip(defs.assignments, range(num_assignments)))
    for metric in defs.ALL_METRICS:
        for proc in defs.ALL_PROCESS:
            basename = metric + defs.FILENAME_SEP + proc
            totals = read_diff_totals(basename, pnum)
            silhouette = calc_assignment_silhouette(totals, pnum)
            print('{:15s}'.format(basename), end=' ')
            for a in defs.assignments:
                aavg = (sum(silhouette[a].values()) /
                        len(silhouette[a].values()))
                print('{:+.2f}'.format(aavg), end=' ')
            print()


function = 1
if __name__ == '__main__':
    if function == 1:  # all vs all (so 115 x 115)
        plot_assignment_sims(versus_all=True, save_to_file=True)
    if function == 2:  # all vs max (so 115 x 1)
        plot_assignment_sims(versus_all=False, save_to_file=True)
    elif function == 3:
        calc_silhouette()
