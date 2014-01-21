import simplejson as json
import mapreduce_common

def map(slug, dims, value, context):
    ping = json.loads(value)
    if ('info' not in ping or
        'simpleMeasurements' not in ping or
        'uptime' not in ping['simpleMeasurements']):
        return
    raw_sm = ping['simpleMeasurements']
    uptime = raw_sm['uptime']
    if uptime < 0:
        return
    if raw_sm.get('debuggerAttached', 0):
        return
    info = mapreduce_common.filterInfo(ping['info'])
    mapreduce_common.addUptime(info, ping)
    for name, dim in mapreduce_common.filterDimensions(dims, info).iteritems():
        context.write((name, dim), (uptime, info))

def reduce(key, values, context):
    if not values:
        return
    aggregate = {}
    lower, upper = mapreduce_common.estQuantile(values, 10, key=lambda x:x[0])
    lower = int(round(lower))
    upper = int(round(upper))
    for uptime, value in values:
        uptime = max(min(uptime, upper), lower)
        for k, v in value.iteritems():
            bucket = aggregate.setdefault(k, {})
            bucket[v] = bucket.get(v, 0) + uptime
    context.write(json.dumps(key), json.dumps(aggregate))
