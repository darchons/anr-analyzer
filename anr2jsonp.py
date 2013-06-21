#!/usr/bin/env python2

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from anr import ANRReport, cluster

def anr2jsonp(threshold, inputfile):

    with open(inputfile, 'r') as f:
        anrs = [ANRReport(l) for l in f]
    for i, a in enumerate(anrs):
        a.line = i
        a.rawData['info']['hasLogcat'] = (len(a.rawData['androidLogcat']) > 100)
    anrfile = os.path.basename(inputfile)

    def comp(left, right):
        linfo = left[0].rawData['info']
        rinfo = right[0].rawData['info']
        for key in linfo:
            if key in rinfo and linfo[key] != rinfo[key]:
                return False
        lm = left[0].mainThread
        rm = right[0].mainThread
        if (lm == rm) < threshold:
            return False
        return not any(l.name == r.name and (l == r) < threshold
            for l in left[0].getBackgroundThreads()
            for r in right[0].getBackgroundThreads())

    clusters = [a for a in cluster(anrs, comp=comp) if a[0].mainThread]
    for clus in clusters:
        clus[0].rawData['info']['file'] = anrfile
        submitted = anrfile.split('-')[-1].split('.')[0]
        clus[0].rawData['info']['submitted'] = '-'.join(
            [submitted[:4], submitted[4:6], submitted[6:]])

    print 'Combined %d ANRs into %d elements.' % (len(anrs), len(clusters))

    return clusters

if __name__ == '__main__':

    import json, os, sys

    if len(sys.argv) < 4:
        print 'Usage: %s <threshold> <inputs> <output>' % sys.argv[0]
        sys.exit(1)

    threshold = float(sys.argv[1])
    inputfiles = sys.argv[2: -1]
    outputfile = sys.argv[-1]
    if os.path.exists(outputfile):
        outputfile = inputfiles[0] + '.jsonp'
    clusters = []

    for inputfile in inputfiles:
        if inputfile.endswith('.jsonp') or inputfile.endswith('.gz'):
            continue
        print 'Processing %s...' % (inputfile)
        clusters.extend(anr2jsonp(threshold, inputfile))

    def getInfo(clus):
        info = {'line': [a.line for a in clus]}
        for key in clus[0].rawData['info']:
            info[key] = clus[0].rawData['info'][key]
        return info

    with open(outputfile, 'w') as f:
        f.write(outputfile.split('/')[-1].split('.')[0].replace('-', '_') + '([');
        f.write(','.join(json.dumps({
            'count': len(clus),
            'main': [str(s) for s in clus[0].mainThread.stack],
            'threads': [{
                'name': t.name,
                'stack': [str(s) for s in t.stack]}
                for t in clus[0].getBackgroundThreads()],
            'info': getInfo(clus)
        }) for clus in clusters))
        f.write(']);')

