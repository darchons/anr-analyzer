# Same as the osdistribution.py example in jydoop
import json
import mapreduce_common

def map(raw_key, raw_dims, raw_value, cx):
    if '"threadHangStats":' not in raw_value:
        return
    try:
        j = json.loads(raw_value)
        raw_sm = j['simpleMeasurements']
        uptime = raw_sm['uptime']
        if uptime < 0:
            return
        if raw_sm.get('debuggerAttached', 0):
            return
        raw_info = j['info']
        info = mapreduce_common.filterInfo(raw_info)
        mapreduce_common.addUptime(info, j)
        dims = mapreduce_common.filterDimensions(raw_dims, info)
    except KeyError:
        pass
    for thread in j['threadHangStats']:
        name = thread['name']
        cx.write((name, None), (dims, info, thread['activity']))
        for hang in thread['hangs']:
            cx.write((name, tuple(hang['stack'])),
                     (dims, info, hang['histogram']))
        cx.write((None, name), (dims, info, uptime))
    if j['threadHangStats']:
        cx.write((None, None), (dims, info, uptime))

def reduce(raw_key, raw_values, cx):
    result = {}

    upper = lower = None
    if raw_key[0] is None:
        lower, upper = mapreduce_common.estQuantile(raw_values, 10, key=lambda x:x[2])
        lower = int(round(lower))
        upper = int(round(upper))

    def merge(dest, src):
        # dest and src are dicts of buckets and counts
        for k, v in src.iteritems():
            if not v:
                continue
            dest[k] = dest.get(k, 0) + v

    def collect(dim, info, counts):
        if not isinstance(counts, dict):
            # int
            counts = max(min(counts, upper), lower)
            for k, v in info.iteritems():
                info_bucket = dim.setdefault(k, {})
                info_bucket[v] = info_bucket.get(v, 0) + counts
            return
        for k, v in info.iteritems():
            info_bucket = dim.setdefault(k, {})
            if v not in info_bucket:
                info_bucket[v] = {k: v for k, v in counts['values'].iteritems() if v}
                continue
            merge(info_bucket[v], counts['values'])

    # uptime measurement
    for dims, info, counts in raw_values:
        for k, dim_val in dims.iteritems():
            collect(result.setdefault(k, {}).setdefault(dim_val, {}),
                    info, counts)

    cx.write(json.dumps(raw_key), json.dumps(result))
