import json

def map(slug, dims, value, context):
    ping = json.loads(value)
    if 'info' not in ping:
        return
    for i, dim in enumerate(dims):
        context.write(tuple(i, dim), ping['info'])

def reduce(key, values, context):
    if not values:
        return
    aggregate = {}
    for value in values:
        for k, v in value.iteritems():
            bucket = aggregate.setdefault(k, {})
            bucket[v] = bucket.get(v, 0) + 1
    context.write(json.dumps(list(key)), json.dumps(aggregate))
