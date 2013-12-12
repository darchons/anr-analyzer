
allowed_infos = [
    'appBuildID',
    'appVersion',
    'appName',
    'appUpdateChannel',
    'locale',
    'device',
    'arch',
    'cpucount',
    'memsize',
    'OS',
    'version',
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
    'appName',
    'appUpdateChannel',
    'appVersion',
    'submission_date',
]

def adjustInfo(info):
    if 'memsize' in info:
        info['memsize'] = (int(info['memsize']) + 64) & (~127)
    if 'version' in info:
        info['version'] = str(info['version']).partition('-')[0]
    if 'adapterRAM' in info:
        info['adapterRAM'] = (int(info['adapterRAM']) + 64) & (~127)
    if 'arch' in info:
        arch = info['arch']
        info['arch'] = ('armv7'
            if ('v7' in arch or (arch == 'arm' and
                                 info.get('hasARMv7', True)))
            else 'armv6')

def filterInfo(raw_info):
    ret = {k: v for k, v in raw_info.iteritems()
           if k in allowed_infos}
    adjustInfo(ret)
    return ret

def filterDimensions(raw_dims):
    return [v for i, v in enumerate(raw_dims)
            if dimensions[i] in allowed_dimensions]
