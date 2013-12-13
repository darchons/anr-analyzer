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
    if uptime <= 0:
        return
    for name, dim in mapreduce_common.filterDimensions(dims, info).iteritems():
        context.write((name, dim), (uptime, info))

def reduce(key, values, context):
    if not values:
        return
    aggregate = {}
    upper = mapreduce_common.quantile(values, 10, upper=True, key=lambda x:x[0])
    lower = mapreduce_common.quantile(values, 10, upper=False, key=lambda x:x[0])
    for uptime, value in values:
        if uptime > upper or uptime < lower:
            continue
        for k, v in value.iteritems():
            bucket = aggregate.setdefault(k, {})
            bucket[v] = bucket.get(v, 0) + uptime * 10 / 8
    context.write(json.dumps(key), json.dumps(aggregate))
