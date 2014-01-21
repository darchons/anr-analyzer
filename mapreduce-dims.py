import re
import simplejson as json
from collections import OrderedDict
from anr import ANRReport
import mapreduce_common

re_subname = re.compile(r'\$\w*\d+')

def processFrame(frame):
    return re_subname.sub('$', frame)

def map(slug, dims, value, context):
    anr = ANRReport(value)
    mainThread = anr.mainThread
    if not mainThread:
        return
    stack = mainThread.stack
    stack = [str(frame).split(':')[1] for frame in stack
             if not frame.isNative]

    # least stable to most stable
    ignoreList = [
        'com.android.internal.',
        'com.android.',
        'dalvik.',
        'android.',
        'java.lang.',
    ]

    def getStack(stack):
        return list(OrderedDict.fromkeys(
            [processFrame(frame) for frame in stack
             if not any(frame.startswith(prefix) for prefix in ignoreList)]))
    key_thread = mainThread.name
    key_stack = getStack(stack)
    while ignoreList and len(key_stack) < 10:
        ignoreList.pop()
        key_stack = getStack(stack)

    def getNativeStack():
        nativeThread = 'GeckoMain (native)'
        nativeMain = anr.getThread('GeckoMain (native)')
        if nativeMain is None:
            return (key_thread, key_stack)
        nativeStack = [str(f) for f in nativeMain.stack if f.isPseudo]
        if not nativeStack:
            return (key_thread, key_stack)
        return (nativeThread, nativeStack)
    if any('sendEventToGeckoSync' in f for f in key_stack):
        key_thread, key_stack = getNativeStack()

    context.write((key_thread, tuple(key_stack)), (
        dims + [slug],
        mapreduce_common.filterDimensions(
            dims, mapreduce_common.filterInfo(anr.rawData['info'])),
        value))

def reduce(key, values, context):
    if not values or len(values) < 5:
        return
    info = {}
    anrs = []
    slugs = []
    for slug, dims, value in values:
        anr = ANRReport(value)
        anrs.append(anr)
        raw_info = mapreduce_common.filterInfo(anr.rawData['info'])
        mapreduce_common.addUptime(raw_info, anr.rawData)
        for dimname, dim in dims.iteritems():
            diminfo = info.setdefault(dimname, {}).setdefault(dim, {})
            for infokey, infovalue in raw_info.iteritems():
                counts = diminfo.setdefault(infokey, {})
                counts[infovalue] = counts.get(infovalue, 0) + 1
        slugs.append(slug)
    sample = max(anrs, key=lambda anr:anr.detail)
    context.write(slugs[0], json.dumps({
        'info': info,
        'threads': [{
                'name': sample.mainThread.name,
                'stack': [str(f) for f in sample.mainThread.stack]
            }] + [{
                'name': t.name,
                'stack': [str(f) for f in t.stack]
            } for t in sample.getBackgroundThreads()],
        'slugs': slugs,
        'display': key[0]
    }))
