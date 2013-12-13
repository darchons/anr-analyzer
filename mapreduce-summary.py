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
    info = mapreduce_common.filterInfo(ping['info'])
    mapreduce_common.addUptime(info, ping)
    uptime = ping['simpleMeasurements']['uptime']
    if uptime < 0:
        return
    for name, dim in mapreduce_common.filterDimensions(dims, info).iteritems():
        context.write((name, dim), uptime)

def reduce(key, values, context):
    if not values:
        return
    upper = mapreduce_common.quantile(values, 10, upper=True)
    lower = mapreduce_common.quantile(values, 10, upper=False)
    limited = [x for x in values if x <= upper and x >= lower]
    context.write(json.dumps(key), json.dumps(
        (len(limited), sum(limited), min(limited), max(limited))))
