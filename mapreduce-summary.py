import json
import mapreduce_common

def map(slug, dims, value, context):
    context.write(None, 1)
    ping = json.loads(value)
    if ('info' not in ping or
        'simpleMeasurements' not in ping or
        'uptime' not in ping['simpleMeasurements']):
        return
    info = mapreduce_common.filterInfo(ping['info'])
    uptime = float(ping['simpleMeasurements']['uptime'])
    if uptime <= 0.0:
        return
    for name, dim in mapreduce_common.filterDimensions(dims, info).iteritems():
        context.write((name, dim), uptime)

def reduce(key, values, context):
    if not values:
        return
    context.write(json.dumps(key), json.dumps((len(values), sum(values))))
