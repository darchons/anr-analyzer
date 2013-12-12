import json, re
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
    def getStack():
        return list(OrderedDict.fromkeys(
            [processFrame(frame) for frame in stack
             if not any(frame.startswith(prefix) for prefix in ignoreList)]))
    stack = getStack()
    while ignoreList and len(stack) < 10:
        ignoreList.pop()
        stack = getStack()
    context.write(tuple(stack), (
        slug,
        mapreduce_common.filterDimensions(
            dims, mapreduce_common.filterInfo(anr.rawData['info'])),
        value))

def reduce(key, values, context):
    if not values:
        return
    info = {}
    anrs = []
    slugs = []
    for slug, dims, value in values:
        anr = ANRReport(value)
        anrs.append(anr)
        if 'info' not in anr.rawData:
            continue
        raw_info = mapreduce_common.filterInfo(anr.rawData['info'])
        for dimname, dim in dims.iteritems():
            diminfo = info.setdefault(dimname, {}).setdefault(dim, {})
            for infokey, infovalue in raw_info.iteritems():
                counts = diminfo.setdefault(infokey, {})
                counts[infovalue] = counts.get(infovalue, 0) + 1
        slugs.append(slug)
    sample = max(anrs, key=lambda anr:anr.detail)
    context.write(hash(key), json.dumps({
        'info': info,
        'threads': [{
                'name': 'main',
                'stack': [str(f) for f in sample.mainThread.stack]
            }] + [{
                'name': t.name,
                'stack': [str(f) for f in t.stack]
            } for t in sample.getBackgroundThreads()],
        'slugs': slugs
    }))
