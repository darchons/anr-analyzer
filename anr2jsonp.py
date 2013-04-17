#!/usr/bin/env python

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
        if (linfo['appID'] != rinfo['appID'] or
            linfo['appVersion'] != rinfo['appVersion'] or
            linfo['appBuildID'] != rinfo['appBuildID'] or
            linfo['version'] != rinfo['version'] or
            linfo['hasLogcat'] != rinfo['hasLogcat']):
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

    with open(outputfile, 'w') as f:
        f.write(outputfile.split('/')[-1].split('.')[0].replace('-', '_') + '([');
        f.write(','.join(json.dumps({
            'count': len(clus),
            'main': [str(s) for s in clus[0].mainThread.stack],
            'threads': [{
                'name': t.name,
                'stack': [str(s) for s in t.stack]}
                for t in clus[0].getBackgroundThreads()],
            'info': {
                'file': clus[0].rawData['info']['file'],
                'line': [a.line for a in clus],
                'appVersion': clus[0].rawData['info']['appVersion'],
                'appBuildID': clus[0].rawData['info']['appBuildID'],
                'submitted': clus[0].rawData['info']['submitted'],
                'androidVersion': clus[0].rawData['info']['version'],
                'hasLogcat': clus[0].rawData['info']['hasLogcat']
            }}) for clus in clusters))
        f.write(']);')

