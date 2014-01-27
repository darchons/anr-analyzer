#!/usr/bin/env python2

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import array, json, re

DEBUG = False

ANR_JAVA_METHOD = re.compile(
    r'([0-9a-zA-Z_\.\$<>]+)(?:.*?\((.*?)(?::(.*))?\))?')
ANR_NATIVE_FUNCTION = re.compile(
    r'(\d+).*? ([0-9a-fA-F]+)(?:.*? (\S*[/\.]\S+))?(?:.*? \((.+)\))?')

THREAD_BLACKLIST = [
    re.compile(r'^GeckoANRReporter$'),
]

THREAD_WHITELIST = [
    re.compile(r'^Gecko'),
    re.compile(r'^Compositor$'),
]

class ANRReport:

    class Thread:

        def __init__(self, name, states, props, stack):
            self.name = name
            self.states = list(states)
            self.props = dict(props)
            self.stack = list(stack)

        def __getitem__(self, index):
            if index in self.props:
                return self.props[index]
            return index in self.states

        def _neMatch(self, selfStack, otherStack):
            # performs a "not-equals" matching using dynamic time warping
            if len(selfStack) == 1:
                return sum(selfStack[0] != s for s in otherStack)
            if len(otherStack) == 1:
                return sum(s != otherStack[0] for s in selfStack)

            left = array.array('d', (0.0 for s in selfStack))
            right = array.array('d', left)
            if DEBUG:
                print ' DTW of size %d and %d' % (
                    len(selfStack), len(otherStack))

            # first element of first column
            right[0] = (selfStack[0] != otherStack[0])
            # other elements of first column
            for j in range(1, len(selfStack)):
                right[j] = (selfStack[j] != otherStack[0]) + right[j - 1]
            if DEBUG:
                print '  column 0 min at %s' % (str(min(zip(
                    range(len(right)), right), key=lambda k: right[k[0]])))
            # other columnns
            for i in range(1, len(otherStack)):
                # move to next column by swapping
                left, right = right, left
                # first element of other column
                right[0] = (selfStack[0] != otherStack[i]) + left[0]
                # other elements of other column
                for j in range(1, len(selfStack)):
                    right[j] = (selfStack[j] != otherStack[i]) + min(
                            left[j], left[j - 1], right[j - 1])
                if DEBUG:
                    print '  column %d min at %s' % (i, str(min(zip(
                        range(len(right)), right), key=lambda k: right[k[0]])))
            # result is the sum at the other corner
            return right[-1]

        def __eq__(self, other):
            if not other or not self.stack or not other.stack:
                return 0.0
            if DEBUG:
                print 'Comparing thread %s to thread %s' % (
                    self.name, other.name)
            # ensure commutativity
            if len(self.stack) < len(other.stack):
                return other == self
            if len(self.stack) == len(other.stack) and self.name < other.name:
                return other == self
            # aStart = bStart = 0
            # if not self.stack[0].isNative or not other.stack[0].isNative:
            if True:
                # don't compare native stack
                aStart = next(i for i in range(len(self.stack))
                    if not self.stack[i].isNative)
                bStart = next(i for i in range(len(other.stack))
                    if not other.stack[i].isNative)
            return 1.0 - (
                self._neMatch(self.stack[aStart:], other.stack[bStart:])) / (
                max(len(self.stack) - aStart, len(other.stack) - bStart))

        def __ne__(self, other):
            return 1.0 - (self == other)

    class StackFrame:

        def __init__(self, frame, isNative, libs=None):
            self.isNative = isNative
            self.isProfiler = self.isPseudo = False
            self.javaMethod = self.javaFile = self.javaLine = None
            self.nativeId = self.nativeAddress = None
            self.nativeLib = self.nativeFunction = None
            try:
                if not isinstance(frame, basestring):
                    self.isNative = self.isProfiler = self.isPseudo = True
                    self._initProfiler(frame, libs)
                elif isNative:
                    self._initNative(frame)
                else:
                    self._initJava(frame)
            except IndexError:
                return

        def _initJava(self, frame):
            # android.os.Handler.handleCallback(Handler.java:615)
            tokens = ANR_JAVA_METHOD.split(frame.strip())
            self.javaMethod = tokens[1]
            self.javaFile = tokens[2]
            self.javaLine = tokens[3]

        def _initNative(self, frame):
            # 03 pc 00023f7d /system/lib/libgui.so \
            #  (android::SensorEventQueue::waitForEvent() const+36)
            tokens = ANR_NATIVE_FUNCTION.split(frame.strip())
            self.nativeId = int(tokens[1], 10)
            self.nativeAddress = int(tokens[2], 16)
            self.nativeLib = tokens[3]
            self.nativeFunction = tokens[4]

        def _initProfiler(self, frame, libs):
            self.natvieId = 0
            self.nativeAddress = 0
            self.nativeLib = ''
            location = frame['location']
            if location[0].isdigit():
                self.isPseudo = False
                address = int(location, 0)
                for lib in libs:
                    if lib['start'] > address or lib['end'] <= address:
                        continue
                    self.nativeLib = lib['name']
                    address -= lib['start'] - (lib['offset'] if 'offset' in lib else 0)
                    break
                self.nativeAddress = address
                location = hex(address)

            self.nativeFunction = location
            if 'line' in frame:
                self.nativeFunction += '+' + str(frame['line'])

        def __str__(self):
            if self.isNative:
                return 'c:%s:%s' % (
                    self.nativeLib if self.nativeLib else '',
                    self.nativeFunction if self.nativeFunction else '')
            return 'j:%s:%s' % (
                self.javaMethod if self.javaMethod else '',
                self.javaLine if self.javaLine else '')

        def _eqNative(self, other):
            aLib = self.nativeLib
            bLib = other.nativeLib
            if not aLib or not bLib:
                return 1.0 if not aLib and not bLib else 0.0
            if (aLib.find('/') < 0) != (bLib.find('/') < 0):
                # strip directory
                aLib = aLib[aLib.rfind('/') + 1:]
                bLib = bLib[bLib.rfind('/') + 1:]
            if aLib and bLib and aLib == bLib:
                return self._eqNativeFunction(
                    self.nativeFunction, other.nativeFunction)
            # compare without directory
            aLib = aLib[aLib.rfind('/') + 1:]
            bLib = bLib[bLib.rfind('/') + 1:]
            if aLib and bLib and aLib == bLib:
                return self._eqNativeFunction(
                    self.nativeFunction, other.nativeFunction)
            return 0.0

        def _eqNativeFunction(self, a, b):
            if not a or not b:
                return 1.0 if not a and not b else 0.0
            # a and b are in the form ns::func(arg)+line
            if (a.find('+') < 0) != (b.find('+') < 0):
                # strip line numbers
                a = a.partition('+')[0]
                b = b.partition('+')[0]
            if (a.find('(') < 0) != (b.find('(') < 0):
                # strip arguments
                a = a.partition('(')[0]
                b = b.partition('(')[0]
            if (a.find(':') < 0) != (b.find(':') < 0):
                # strip namespaces
                a = a[a.rfind(':') + 1:]
                b = b[b.rfind(':') + 1:]
            if a and b and a == b:
                return 1.0
            # compare without line number
            a = a.partition('+')[0]
            b = b.partition('+')[0]
            if a and b and a == b:
                return 1.0
            # compare without arguments
            a = a.partition('(')[0]
            b = b.partition('(')[0]
            if a and b and a == b:
                return 0.8
            # compare without namespaces
            a = a[a.rfind(':') + 1:]
            b = b[b.rfind(':') + 1:]
            if a and b and a == b:
                return 0.4
            return 0.0

        def _eqJava(self, other):
            # aLine = self.javaLine
            # bLine = other.javaLine
            # if aLine and bLine:
            #     aLine = int(self.javaLine.strip('~'), 10)
            #     bLine = int(other.javaLine.strip('~'), 10)
            #     if 10 * abs(aLine - bLine) / max(aLine, bLine) > 0:
            #         return 0.8 * self._eqJavaMethod(
            #                 self.javaMethod, other.javaMethod)
            return self._eqJavaMethod(self.javaMethod, other.javaMethod)

        def _eqJavaMethod(self, a, b):
            if not a or not b:
                return 0.0
            # a and b are in the form pkg.cls$child.method
            if a and b and a == b:
                return 1.0
            aTokens = a.split('.')
            aClass = aTokens[-2].partition('$')
            aMethod = aTokens[-1]
            bTokens = b.split('.') # package, 0.2 of weight
            bClass = bTokens[-2].partition('$') # 0.3+0.1 of weight
            bMethod = bTokens[-1] # 0.4 of weight
            if aTokens[:-2] != bTokens[:-2]:
                return 0.0
            if aClass[0] != bClass[0]:
                return 0.2
            return ((0.1 if aClass[-1] == bClass[-1] else 0.0) +
                    (0.4 if aMethod == bMethod else 0.0) + 0.5)

        def __eq__(self, other):
            if DEBUG:
                print '   comparing %s to %s' % (self, other)
            if self.isNative != other.isNative:
                return 0.0
            if self.isNative:
                return self._eqNative(other)
            return self._eqJava(other)

        def __ne__(self, other):
            return 1.0 - (self == other)

    def _parseLine(self, line, name, states, props, stack):
        line = line.strip()
        if not line:
            return

        if line.startswith('"'):
            # new thread
            if name:
                # save previous thread
                self.threads.append(ANRReport.Thread(name, states, props, stack))
                del states[:]
                props.clear()
                del stack[:]
            # "main" prio=5 tid=1 SUSPENDED
            tokens = line[1:].partition('"')
            name = tokens[0]
            for token in tokens[2].split():
                if '=' not in token:
                    states.append(token)
                    continue
                prop = token.partition('=')
                props[prop[0]] = prop[2]
            return name

        if name and (line.startswith('|') or line.startswith('>')):
            # | group="main" sCount=1 dsCount=0 obj=0x41734508 self=0x41723fb0
            # | sysTid=16806 nice=0 sched=0/0 cgrp=apps handle=1075207984
            # | schedstat=( 22141839338 608612447 4633 ) utm=2191 stm=22 core=3
            line = line[1:]
            if '=' in line:
                # properties
                line = ''.join([(s if i & 1 else s.replace(' ', '\0'))
                    for i, s in enumerate(line.split('"'))])
                for prop in line.split('\0'):
                    if not prop:
                        continue
                    prop = prop.partition('=')
                    if not prop[1]:
                        states.append(prop[0])
                        continue
                    props[prop[0]] = prop[2]
            return

        if name and line.startswith('at '):
            stack.append(ANRReport.StackFrame(line[3:], isNative=False))
            return

        if name and line.startswith('#'):
            stack.append(ANRReport.StackFrame(line[1:], isNative=True))
            return

    def _parseProfiler(self):
        if 'threads' not in self._nativeStack:
            self._nativeStack = None
            return

        libs = {}
        if 'libs' in self._nativeStack:
            libs = json.loads(self._nativeStack['libs'])
            self._nativeStack['libs'] = libs

        for t in self._nativeStack['threads']:
            if ('samples' not in t or
                len(t['samples']) == 0 or
                'frames' not in t['samples'][0]):
                continue
            stack = [ANRReport.StackFrame(f, True, libs)
                    for f in reversed(t['samples'][0]['frames'])]
            self.threads.append(ANRReport.Thread(
                    t['name'] + ' (native)', [], {}, stack))

    def __init__(self, raw):
        self.rawData = json.loads(raw)
        self.threads = []
        name = None
        states = []
        props = {}
        stack = []
        # parse ANR
        for line in self.rawData['androidANR'].splitlines():
            tmp = self._parseLine(line, name, states, props, stack)
            name = tmp if tmp else name
        if name:
            # save last thread
            self.threads.append(ANRReport.Thread(name, states, props, stack))
        # process native stack
        self._nativeStack = None
        if 'androidNativeStack' in self.rawData:
            nativeStack = self.rawData['androidNativeStack']
            self._nativeStack = (json.loads(nativeStack)
                if isinstance(nativeStack, basestring) else nativeStack)
            self._parseProfiler()

    @property
    def log(self):
        return self['androidLogcat']

    @property
    def nativeStack(self):
        return self._nativeStack

    def getThread(self, name):
        try:
            return next(t for t in self.threads if t.name == name)
        except StopIteration:
            return None

    @property
    def mainThread(self):
        return self.getThread('main')

    def getBackgroundThreads(self):
        main = self.mainThread
        for t in self.threads:
            if t is main:
                continue
            if not t.name or not t.stack:
                continue
            if not any(bl.search(t.name) for bl in THREAD_WHITELIST):
                continue
            if any(bl.search(t.name) for bl in THREAD_BLACKLIST):
                continue
            yield t

    @property
    def detail(self):
        t = self.mainThread
        return 0 if not t else (
            len(t.stack) * 2 +
            sum(len(t.stack) for t in self.getBackgroundThreads()))

    def __eq__(self, other):
        return self.mainThread == other.mainThread

def cluster(anrs, threshold=None, comp=None):
    if len(anrs) == 1:
        return [anrs]

    if not comp:
        def defComp(left, right):
            return (left[0] == right[0]) >= threshold
        comp = defComp

    left = cluster(anrs[:len(anrs) / 2],
        threshold=threshold, comp=comp)
    right = cluster(anrs[len(anrs) / 2:],
        threshold=threshold, comp=comp)
    ret = []
    for r in right:
        # extend left cluster if right cluster matches left cluster
        i = next((i for i in range(len(left)) if comp(left[i], r)), -1)
        if i == -1:
            ret.append(r)
            continue
        l = left[i]
        if l[0].detail > r[0].detail:
            l.extend(r)
        else:
            r.extend(l)
            left[i] = r
    ret.extend(left)
    return ret

if __name__ == '__main__':

    import sys, time

    if len(sys.argv) != 3:
        print 'Usage: %s <threshold> <input>' % (sys.argv[0])
        sys.exit(1)

    starttime = time.time()

    threshold = float(sys.argv[1])
    with open(sys.argv[2], 'r') as f:
        anrs = [ANRReport(l) for l in f]

    clusters = cluster(anrs, threshold=threshold)
    clusters.sort(key=lambda c: len(c))

    for i, clus in enumerate(clusters):
        print 'Cluster %d: %d member(s), stack:' % (i + 1, len(clus))
        for j, c in enumerate(clus):
            print ' Member %d:' % (j + 1)
            mainThread = c.mainThread
            if mainThread:
                for s in mainThread.stack:
                    print '  ' + str(s)
        print

    print 'Took %f seconds\n' % (time.time() - starttime)
    sys.exit(1)

