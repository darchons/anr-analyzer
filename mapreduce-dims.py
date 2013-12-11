import json, re
from collections import OrderedDict
from anr import ANRReport
import mapreduce_common

re_subname = re.compile(r'\$\w+')

def processFrame(frame):
    return re_subname.sub('', frame)

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
        'android.view.',
        'android.',
        'java.lang.',
    ]
    popList = ignoreList.pop
    def getStack():
        return list(OrderedDict.fromkeys(
            [processFrame(frame) for frame in stack
             if any(frame.startswith(prefix) for prefix in ignoreList)]))
    stack = getStack()
    while ignoreList and len(stack) < 10:
        popList()
        stack = getStack()
    context.write(tuple(stack), (slug, dims, value))

def reduce(key, values, context):
    if not values:
        return
    info = {k: {} for k in mapreduce_common.allowed_dimensions}
    anrs = []
    slugs = []
    for slug, dims, value in values:
        anr = ANRReport(value)
        anrs.append(anr)
        if 'info' not in anr.rawData:
            continue
        raw_info = mapreduce_common.filterInfo(anr.rawData['info'])
        for i, dim in enumerate(dims):
            dimname = mapreduce_common.dimensions[i]
            if dimname not in mapreduce_common.allowed_dimensions:
                continue
            diminfo = info[dimname].setdefault(dim, {})
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
