import json
from anr import ANRReport

def map(key, dims, value, context):
    # save all ANR reports using submission date as key
    anr = ANRReport(value)
    mainThread = anr.mainThread()
    if not mainThread:
        return
    stack = mainThread.stack
    stack = [str(frame) for frame in stack if not frame.isNative]
    context.write(tuple(stack), (key, dims, anr))

def reduce(key, values, context):
    info = {}
    for slug, dims, anr in values:
        if 'info' not in anr.rawData:
            continue
        for dim in dims:
            diminfo = sampleinfo.setdefault(dim, {})
            for infokey, infovalue in anr.rawData['info'].iteritems():
                counts = diminfo.setdefault(infokey, {})
                counts[infovalue] = counts.get(infovalue, 0) + 1
            diminfo.setdefault('slug', []).append(slug)
    sample = max(values, key=lambda v:v[2].detail)[2]
    context.write(hash(key), json.dumps({
        'info': info,
        'threads': [{
                'name': 'main',
                'stack': [str(f) for f in sample.mainThread.stack]
            }].extend([{
                'name': t.name,
                'stack': [str(f) for f in t.stack]
            } for t in sample.getBackgroundThreads()])
    }))
