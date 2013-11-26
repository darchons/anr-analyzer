#!/usr/bin/env python2

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

if __name__ == '__main__':

    import json, os, sys
    from anr import ANRReport

    def printLine(l):
        anr = ANRReport(l)
        traces = anr.rawData.pop('androidANR', None)
        logcat = anr.rawData.pop('androidLogcat', None)
        nativeStack = anr.rawData.pop('androidNativeStack', None)
        print json.dumps(anr.rawData, indent=4)
        print '===== raw traces ====='
        print traces
        print '===== end raw traces ====='
        print '===== raw logcat ====='
        print logcat
        print '===== end raw logcat ====='
        if anr.nativeStack:
            print '===== raw native stack ====='
            print json.dumps(anr.nativeStack, indent=4)
            print '===== end raw native stack ====='

    if len(sys.argv) != 3 and len(sys.argv) != 1:
        print 'Usage %s [<file> <lines>]' % (sys.argv[0])
        sys.exit(1)

    if len(sys.argv) == 1:
        l = sys.stdin.readline()
        while l:
            print '===== ANR ====='
            printLine(l)
            print '===== END ANR ====='
            print
            l = sys.stdin.readline()
        sys.exit(0)

    lines = [int(l, 0) for l in sys.argv[2].split(',')]

    with open(sys.argv[1], 'r') as f:
        line = -1
        for l in f:
            line += 1
            if line not in lines:
                continue
            print '===== ANR file %s line %d =====' % (
                os.path.basename(sys.argv[1]), line)
            printLine(l)
            print '===== END ANR ====='
            print
