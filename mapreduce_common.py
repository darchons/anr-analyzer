
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

def adjustInfo(info):
    if 'memsize' in info and int(info['memsize']) > 0:
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

    if 'cpucount' not in info or int(info['cpucount']) <= 0:
        info['cpucount'] = None

    if 'OS' in info:
        info['platform'] = info['OS']
    else:
        info['platform'] = None

    if 'adapterRAM' in info:
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
    maxs.sort()
    if not len(maxs):
        return max(values) if upper else min(values)
    for v in (key(x) for x in values[len(values) / n:]):
        if upper and v > maxs[0]:
            maxs[0] = v
            maxs.sort()
        elif not upper and v < maxs[-1]:
            maxs[-1] = v
            maxs.sort()
    return maxs[0] if upper else maxs[-1]
