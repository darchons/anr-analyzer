
allowed_infos = [
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
    'appBuildID',
    'submission_date',
]

def adjustInfo(info):
    if 'memsize' in info:
        info['memsize'] = (info['memsize'] + 64) & (~127)
    if 'version' in info:
        info['version'] = info['version'].partition('-')[0]
    if 'adapterRAM' in info:
        info['adapterRAM'] = (info['adapterRAM'] + 64) & (~127)

def filterInfo(raw_info):
    ret = {k: v for k, v in raw_info.iteritems()
           if k in allowed_infos}
    adjustInfo(ret)
    return ret

def filterDimensions(raw_dims):
    return [v for i, v in enumerate(raw_dims)
            if dimensions[i] in allowed_dimensions]
