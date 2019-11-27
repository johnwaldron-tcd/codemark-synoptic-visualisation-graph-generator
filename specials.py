#!/usr/bin/python3
'''
    Process the 'special' sets of programs:
        (1) INST: sample solutions from the course instructor
        (2) CIRC: the circulated solutions (only 10 of 11 projects)
'''

import os
import matplotlib.pyplot as plt

import defs
import compare
import plot_graphs


def copy_specials():
    '''
        Take the special files and copy then to a new directory.
    '''
    for special_kind in defs.ALL_SPECIALS:
        src_dir = defs.special_src[special_kind]
        _, _, files = next(os.walk(src_dir))
        files = [f for f in files if f.endswith(defs.VERILOG_SUFFIX)]
        for vfilename in files:
            newfilename = special_kind + defs.FILENAME_SEP + vfilename
            compare.copy_file(src_dir, vfilename,
                              defs.SPECIAL_ORIG, newfilename,
                              omit_first=False)


def compare_all(student_dir, special_dir, cmpfunc):
    '''
        Compare the special submission for a program against all students
        Return a list of triples: (file1, file2, similarity).
        This is not NxN but 1xN: special vs all.
    '''
    _, _, specialfiles = next(os.walk(special_dir))
    specialfiles = [f for f in specialfiles if f.endswith(defs.VERILOG_SUFFIX)]
    _, _, studentfiles = next(os.walk(student_dir))
    studentfiles = [f for f in studentfiles if f.endswith(defs.VERILOG_SUFFIX)]
    metrics = []
    for fn1 in specialfiles:
        lines1 = compare.read_file(special_dir, fn1)
        if (not lines1) or len(lines1) == 0:
            continue
        for fn2 in studentfiles:  # if symmetric, use files[i+1:]:
            lines2 = compare.read_file(student_dir, fn2)
            if (not lines2) or len(lines2) == 0:
                continue
            sim = round(cmpfunc(lines1, lines2) * 100)
            metrics.append((fn1, fn2, sim))
    return sorted(metrics, key=lambda t: t[0]+t[1])


def do_one_compare(outpath, student_dir, special_dir, cmpfunc):
    '''
        Compare all programs in datadir, write results to output file.
    '''
    metrics = compare_all(student_dir, special_dir, cmpfunc)
    with open(outpath, 'w') as fh:
        for s1, s2, m in metrics:
            fh.write('{} {} {}\n'.format(s1, s2, m))
    print('Sim values written to {}.'.format(outpath))


def compare_specials():
    '''
        Compare the specials against the student submissions.
        Use all metrics, and do both original and clean.
        Write comparison triples to files: special-metric-proc.dat
    '''
    metrics = {
        'jaccard': compare.jaccard,
        'tversky': compare.tv_asymmetric,
        'sequence': compare.sm_compare
    }
    for (metric, cmpfunc) in metrics.items():
        for proc in defs.ALL_PROCESS:
                special_dir = defs.special_dir(proc)
                student_dir = defs.latest_dir(proc)
                outpath = defs.special_filename(metric, proc)
                do_one_compare(outpath, student_dir, special_dir, cmpfunc)


def read_special_sim_all(simfile, special_kind):
    '''
        Read the similarity data from one file and group by assignment.
        So return a dict, mapping assignment to list of sim values,
        for all students doing that assignment (vs specials).
    '''
    sims = {k: [] for k in defs.assignments}
    with open(simfile, 'r') as fh:
        for line in fh:
            skind, a1, stu, a2, sim = line.strip().replace('-', ' ').split()
            if a1 == a2 and skind == special_kind:  # within one project
                sims[a1].append(int(sim))
    # Make sure every project has at least one data point:
    for simvals in sims.values():
        if len(simvals) == 0:
            simvals.append(0)
    return sims


def plot_special_sims(special_kind, metric, processes):
    '''
        Plot all the violin plots in a single figure.
        Kind and metric are fixed, so three plots (orig/clean/token).
    '''
    assert special_kind in defs.ALL_SPECIALS, special_kind
    assert metric in defs.ALL_METRICS, metric
    for j, proc in enumerate(processes):
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(7, 5))
        simfile = defs.special_filename(metric, proc)
        sims = read_special_sim_all(simfile, special_kind)
        basename = defs.FILENAME_SEP.join([special_kind, metric, proc])
        plot_graphs.plot_one_violin(ax, sims, metric, proc)
        # and write to file:
        basename = defs.FILENAME_SEP.join(['violin', special_kind, proc])
        outfile = os.path.join(defs.GRAPHS_DIR,
                               basename + defs.GRAPHS_SUFFIX)
        plt.savefig(outfile, bbox_inches='tight')
        print(' Violin plots written to {}'.format(basename))


function = 1
if __name__ == '__main__':
    if function == 0:
        compare_specials()
    elif function == 1:
        for special_kind in [defs.SPECIAL_CIRC, defs.SPECIAL_INST]:
            plot_special_sims(special_kind, 'jaccard', defs.ALL_PROCESS)
