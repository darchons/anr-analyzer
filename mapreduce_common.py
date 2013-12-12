
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
        info['memsize'] = 0

    if 'version' in info and 'OS' in info:
        info['os'] = (str(info['OS']) + ' ' +
            '.'.join(str(info['version']).split('-')[0].split('.')[:2]))
    elif 'OS' in info:
        info['os'] = str(info['OS'])
    else:
        info['os'] = 'unknown'

    if 'cpucount' not in info or int(info['cpucount']) <= 0:
        info['cpucount'] = -1

    if 'OS' in info:
        info['platform'] = info['OS']

    if 'adapterRAM' in info:
        info['adapterRAM'] = (int(info['adapterRAM']) + 64) & (~127)

    if 'arch' in info:
        arch = info['arch']
        info['arch'] = ('armv7'
            if ('v7' in arch or (arch == 'arm' and
                                 info.get('hasARMv7', True)))
            else 'armv6')

def filterInfo(raw_info):
    adjustInfo(raw_info)
    return {k: v for k, v in raw_info.iteritems()
            if k in allowed_infos}

def filterDimensions(raw_dims, raw_info):
    return {dim: (raw_dims[dimensions.index(dim)]
                  if dim not in raw_info else raw_info[dim])
            for dim in allowed_dimensions}
