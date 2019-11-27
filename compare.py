#!/usr/bin/python3
'''
    Process the full set of student programs and then
    save the latest version (raw or cleaned) in a new directory.
    Generate a file with the similarities, each line of the form:
        s1-p1 s2-p2 perc
    i.e. for students s1 and s2, doing projects p1 and p2, the sim is perc.
    Here p1 and p2 are the filenames of the projects (e.g. 'DecimalAdder.v')
    The simililarity perc is always an integer between 0 and 100.
'''

import os
import codecs

from difflib import SequenceMatcher

import defs


class StudentRecord:
    '''
        For a single student, store a dict of all their submissions.
        The dict is indexed by filename (i.e. assignment).
        Each submission is a (time, jobnum) pair.
    '''
    def __init__(self, id):
        self.id = id
        self.submits = {}

    def add_submit(self, vfile, time, jobnum):
        ''' Add a new submission to the list'''
        if vfile not in self.submits:
            self.submits[vfile] = []
        self.submits[vfile].append((time, jobnum))

    def sort_submits(self):
        '''Sor the suybmissions so most recent one for each file is last'''
        for submit_list in self.submits.values():
            submit_list.sort(key=lambda s: s[0])


def get_students(dirname=defs.DATAROOT):
    '''
        Go through all the submissions and group them by student id.
        Return a dict mapping student id to StudentRecord objects.
    '''
    students = {}
    _, _, files = next(os.walk(dirname))
    files = [f for f in files if f.endswith(defs.JW_FILE_SUFFIX)]
    print('Reading {} files from {}...'.format(
            len(files), os.path.basename(dirname)))
    for filename in files:
        # Trim suffix, split filename into fields:
        field = filename[:-len(defs.JW_FILE_SUFFIX)].split(defs.FILENAME_SEP)
        student_id = field[1]  # anonymised student id
        kind = field[2]
        time = defs.FILENAME_SEP.join(field[3:9])
        jobnum = field[9]
        if student_id not in students:
            students[student_id] = StudentRecord(student_id)
        if kind == defs.SUBMIT:
            filepath = os.path.join(dirname, filename)
            first_line = open(filepath, 'r').readline()
            line_data = first_line.strip().split()
            vfile = line_data[2]
            students[student_id].add_submit(vfile, time, jobnum)
    return students


def copy_file(source_dir, oldfilename, target_dir, newfilename,
              omit_first=True):
    '''
        Open oldfile, write to target_dir/newfile.
    '''
    # Read in the old file:
    oldfilepath = os.path.join(source_dir, oldfilename)
    with codecs.open(oldfilepath,
                     'r', encoding='utf-8', errors='ignore') as fh:
        lines = [line.rstrip('\n') for line in fh]
    if omit_first:  # Throw away first line
        lines = lines[1:]
    # Delete blank lines:
    nblines = [nb for nb in lines if len(nb) > 0]
    # Write out to the new file:
    newfilepath = os.path.join(target_dir, newfilename)
    with open(newfilepath, 'w') as fh:
        fh.write('\n'.join(nblines))


def save_latest(students, target_dir):
    '''
        Save the latest version of each file for each student.
        New file name looks like: target_dir/XXX-Filename.v
    '''
    for s in students.values():
        s.sort_submits()
        for vfilename, sublist in s.submits.items():
            time, jobnum = sublist[-1]
            oldfilename = 'Anon-{}-submit-{}-{}{}'.format(
                            s.id, time, jobnum, defs.JW_FILE_SUFFIX)
            newfilename = s.id + defs.FILENAME_SEP + vfilename
            copy_file(defs.DATAROOT, oldfilename,
                      target_dir, newfilename, True)


def collect_latest():
    students = get_students()
    print('Read data for', len(students), 'students.')
    orig_dir = defs.latest_dir('orig')
    print('Writing to', orig_dir)
    save_latest(students, orig_dir)


def _line_is_junk(s):
    '''Ignore these lines in every file (for SequenceMatcher)'''
    return len(s.strip()) == 0


def sm_compare(f1, f2):
    '''Compare two files using a SequenceMatcher object'''
    sm = SequenceMatcher(_line_is_junk, f1, f2)
    return sm.ratio()


def tversky(f1, f2, alpha, beta):
    '''Calculate the Tversky distance betwen two lists (as sets)'''
    sX = set(f1)
    sY = set(f2)
    num_common = len(sX & sY)
    xmy = len(sX - sY)
    ymx = len(sY - sX)
    denom = num_common + (alpha * xmy) + (beta * ymx)
    return num_common / denom


def jaccard(f1, f2):
    '''Calculate the Jaccard distance betwen two lists (as sets)'''
    return tversky(f1, f2, alpha=1, beta=1)


def tv_asymmetric(f1, f2):
    '''Calculate the distance betwen two lists as a prop of the first'''
    return tversky(f1, f2, alpha=1, beta=0)


def count_common(f1, f2):
    '''Return the number of lines these files have in common'''
    s1 = set(f1)
    s2 = set(f2)
    num_common = len(s1 & s2)
    return num_common


def read_file(dirname, filename):
    filepath = os.path.join(dirname, filename)
    with open(filepath, 'r') as fh:
        lines = fh.readlines()
    return lines


def compare_all(dirname, myfilter, cmpfunc):
    ''' Compare the latest submission for a program for all students
        Do a full NxN comparison, in case cmpfunc is asymmetric.
        Return a list of triples: (file1, file2, similarity)
    '''
    # What progress intervals do you want printed (list of percentages)
    progress = list(range(0, 100, 10))
    _, _, files = next(os.walk(dirname))
    files = [f for f in files if myfilter(f)]
    metrics = []
    for i, fn1 in enumerate(files):
        if len(progress) > 0 and int(i*100/len(files)) == progress[0]:
            print('{}%'.format(progress[0]), flush=True, end=' ')
            progress = progress[1:]
        lines1 = read_file(dirname, fn1)
        if (not lines1) or len(lines1) == 0:
            continue
        for fn2 in files:  # if symmetric, use files[i+1:]:
            lines2 = read_file(dirname, fn2)
            if (not lines2) or len(lines2) == 0:
                continue
            sim = round(cmpfunc(lines1, lines2) * 100)
            metrics.append((fn1, fn2, sim))
    return sorted(metrics, key=lambda t: t[0]+t[1])


def do_one_compare(outfile, datadir, cmpfunc):
    '''
        Compare all programs in datadir, write results to output file.
    '''
    def _file_filter(filename):
        return filename.endswith(defs.VERILOG_SUFFIX)
    print(outfile, end=': ', flush=True)
    metrics = compare_all(datadir, _file_filter, cmpfunc)
    outpath = os.path.join(datadir, '..', outfile+defs.DATA_SUFFIX)
    with open(outpath, 'w') as fh:
        for s1, s2, m in metrics:
            fh.write('{} {} {}\n'.format(s1, s2, m))
    print('\n\t- written to ', outpath)


def do_all_compare():
    metrics = {
        'jaccard': jaccard, 'tversky': tv_asymmetric, 'sequence': sm_compare
    }
    for (metric, cmpfunc) in metrics.items():
        for proc in defs.ALL_PROCESS:
                src_dir = defs.latest_dir(proc)
                basename = metric + defs.FILENAME_SEP + proc
                do_one_compare(basename, src_dir, cmpfunc)


function = 2
if __name__ == '__main__':
    if function == 1:
        collect_latest()
    else:
        do_all_compare()
