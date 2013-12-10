import json

def map(slug, dims, value, context):
    ping = json.loads(value)
    if ('info' not in ping or
        'simpleMeasurements' not in ping or
        'uptime' not in ping['simpleMeasurements']):
        return
    info = ping['info']
    uptime = ping['simpleMeasurements']['uptime']
    for i, dim in enumerate(dims):
        context.write((i, dim), (uptime, ping['info']))

def reduce(key, values, context):
    if not values:
        return
    aggregate = {}
    for uptime, value in values:
        for k, v in value.iteritems():
            bucket = aggregate.setdefault(k, {})
            bucket[v] = bucket.get(v, 0) + uptime
    context.write(json.dumps(list(key)), json.dumps(aggregate))
