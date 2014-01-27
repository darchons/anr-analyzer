import json
import mapreduce_common

def map(slug, dims, value, context):
    context.write("all", 1)
    ping = json.loads(value)
    if ('info' not in ping or
        'simpleMeasurements' not in ping or
        'uptime' not in ping['simpleMeasurements']):
        context.write("corrupt", 1)
        return
    raw_sm = ping['simpleMeasurements']
    uptime = raw_sm['uptime']
    if uptime < 0:
        return
    if raw_sm.get('debuggerAttached', 0):
        return
    info = mapreduce_common.filterInfo(ping['info'])
    mapreduce_common.addUptime(info, ping)
    aggregate = dict(info.items() +
        mapreduce_common.filterDimensions(dims, info).items())
    for name, dim in aggregate.iteritems():
        context.write((name, dim), uptime)

def reduce(key, values, context):
    if not values:
        return
    lower, upper = mapreduce_common.estQuantile(values, 4)
    median = int(round(mapreduce_common.estQuantile(values, 2)[0]))
    lower = int(round(lower))
    upper = int(round(upper))
    context.write(json.dumps(key), json.dumps((
        len(values), median, lower, upper
    )))
