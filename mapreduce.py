import json, re
from anr import ANRReport

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
    stack = [processFrame(frame) for frame in stack
             if any(frame.startswith(prefix) for prefix in ignoreList)]
    while ignoreList and len(stack) < 10:
        ignoreList.pop()
        stack = [processFrame(frame) for frame in stack
                 if any(frame.startswith(prefix) for prefix in ignoreList)]
    context.write(tuple(stack), (slug, dims, value))

def reduce(key, values, context):
    if not values:
        return
    info = [{} for i in range(len(values[0][1]))]
    anrs = []
    slugs = []
    for slug, dims, value in values:
	anr = ANRReport(value)
        anrs.append(anr)
        if 'info' not in anr.rawData:
            continue
        for i, dim in enumerate(dims):
            diminfo = info[i].setdefault(dim, {})
            for infokey, infovalue in anr.rawData['info'].iteritems():
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
