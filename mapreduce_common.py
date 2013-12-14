
allowed_infos = [
    'appName',
    'appVersion',
    'appUpdateChannel',
    'appBuildID',
    'locale',
    'device',
    'cpucount',
    'memsize',
    'os',
    'arch',
    'platform',
    'adapterVendorID',
    'adapterRAM',
    'uptime',
]

dimensions = [
    'reason',
    'appName',
    'appUpdateChannel',
    'appVersion',
    'appBuildID',
    'submission_date',
]

allowed_dimensions = [
    'submission_date',
    'appName',
    'appVersion',
    'os',
    'cpucount',
    'memsize',
]

def addUptime(info, ping):
    uptime = ping['simpleMeasurements']['uptime']
    if uptime >= 40320:
        uptime = '>4w'
    elif uptime >= 10080:
        uptime = '1w-4w'
    elif uptime >= 1440:
        uptime = '1d-1w'
    elif uptime >= 240:
        uptime = '3h-1d'
    elif uptime >= 30:
        uptime = '30m-3h'
    elif uptime >= 5:
        uptime = '5m-30m'
    elif uptime >= 1:
        uptime = '1m-5m'
    elif uptime >= 0:
        uptime = '<1m'
    else:
        return
    info['uptime'] = uptime

def adjustInfo(info):
    if ('memsize' in info and
        str(info['memsize']).isdigit() and
        int(info['memsize']) > 0):
        info['memsize'] = (int(info['memsize']) + 64) & (~127)
    else:
        info['memsize'] = None

    if 'version' in info and 'OS' in info:
        info['os'] = (str(info['OS']) + ' ' +
            '.'.join(str(info['version']).split('-')[0].split('.')[:2]))
    elif 'OS' in info:
        info['os'] = str(info['OS'])
    else:
        info['os'] = None

    if ('cpucount' in info and
        str(info['cpucount']).isdigit() and
        int(info['cpucount']) > 0):
        info['cpucount'] = int(info['cpucount'])
    else:
        info['cpucount'] = None

    if 'OS' in info:
        info['platform'] = info['OS']
    else:
        info['platform'] = None

    if ('adapterRAM' in info and
        str(info['adapterRAM']).isdigit() and
        int(info['adapterRAM']) > 0):
        info['adapterRAM'] = (int(info['adapterRAM']) + 64) & (~127)
    else:
        info['adapterRAM'] = None

    if 'arch' in info:
        arch = info['arch']
        if 'arm' in arch:
            info['arch'] = ('armv7'
                if ('v7' in arch or info.get('hasARMv7', 'v6' not in arch))
                else 'armv6')

def filterInfo(raw_info):
    adjustInfo(raw_info)
    return {k: (raw_info[k]
                if (k in raw_info and raw_info[k] is not None)
                else 'unknown')
            for k in allowed_infos}
    # return {k: v for k, v in raw_info.iteritems()
    #         if k in allowed_infos}

def filterDimensions(raw_dims, raw_info):
    return {dim: (raw_dims[dimensions.index(dim)]
                  if dim not in raw_info else raw_info[dim])
            for dim in allowed_dimensions}

def quantile(values, n, upper=True, key=lambda x:x):
    maxs = [key(x) for x in values[: len(values) / n]]
    curidx, curmin = (min(enumerate(maxs), key=lambda x:x[1]) if upper else
                      max(enumerate(maxs), key=lambda x:x[1]))
    if not len(maxs):
        return max(values) if upper else min(values)
    for v in (key(x) for x in values[len(values) / n:]):
        if ((upper and v <= curmin) or
            (not upper and v >= curmin)):
            continue
        maxs[curidx] = v
        curidx, curmin = (min(enumerate(maxs), key=lambda x:x[1]) if upper else
                          max(enumerate(maxs), key=lambda x:x[1]))
    return curmin
