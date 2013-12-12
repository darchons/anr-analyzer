import json
import mapreduce_common

def map(slug, dims, value, context):
    ping = json.loads(value)
    if ('info' not in ping or
        'simpleMeasurements' not in ping or
        'uptime' not in ping['simpleMeasurements']):
        return
    info = mapreduce_common.filterInfo(ping['info'])
    uptime = ping['simpleMeasurements']['uptime']
    for name, dim in mapreduce_common.filterDimensions(dims, info).iteritems():
        context.write((name, dim), (uptime, info))

def reduce(key, values, context):
    if not values:
        return
    aggregate = {}
    for uptime, value in values:
        for k, v in value.iteritems():
            bucket = aggregate.setdefault(k, {})
            bucket[v] = bucket.get(v, 0) + uptime
    context.write(json.dumps(key), json.dumps(aggregate))
