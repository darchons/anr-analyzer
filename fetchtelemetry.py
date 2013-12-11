#!/usr/bin/python2

import gzip, os, json, subprocess, sys, tempfile

def runJob(job, dims, workdir, outfile, local=False):
    with tempfile.NamedTemporaryFile('w', suffix='.json', dir=workdir) as filterfile:
        filterfile.write(json.dumps({
            'version': 1,
            'dimensions': dims
        }))
        filterfile.flush()

        args = ['python', '-m', 'mapreduce.job',
                os.path.join(os.path.dirname(sys.argv[0]), job),
                '--input-filter', filterfile.name,
                '--num-mappers', '16',
                '--num-reducers', '4',
                '--data-dir', local ? os.path.join(workdir, 'cache') : workdir,
                '--work-dir', workdir,
                '--output', outfile.name,
                '--bucket', 'telemetry-published-v1']
        if local:
            args.append('--local-only')

        env = os.environ
        print 'Calling %s' % (str(' '.join(args)))
        ret = subprocess.call(args, env=env)
        if ret:
            print 'Error %d' % (ret)
            sys.exit(ret)

def saveFile(outdir, name, index, data, prefix=''):
    fn = prefix + name + '.json.gz'
    with gzip.open(os.path.join(outdir, fn), 'wb') as outfile:
        outfile.write(json.dumps(data))
    index[name] = fn

def processDims(index, dims, jobfile, outdir):
    mainthreads = {}
    backgroundthreads = {}
    slugs = {}
    dimsinfo = [{} for i in range(len(dims))]
    dimvalues = [set() for i in range(len(dims))]
    allowed_infos = {}
    for line in jobfile:
        anr = json.loads(line.partition('\t')[2])
        slug = anr['slugs'][0]
        slugs[slug] = anr['slugs']
        mainthreads[slug] = anr['threads'][:1]
        backgroundthreads[slug] = anr['threads'][1:]
        info = anr['info']
        for i, infocounts in enumerate(info):
            for key, value in infocounts.iteritems():
                dimsinfo[i].setdefault(slug, {})[key] = value
                dimvalues[i].add(key)
                for k, v in value.iteritems():
                    allowed_infos.setdefault(k, set()).update(v.iterkeys())

    saveFile(outdir, 'slugs', index, slugs)
    saveFile(outdir, 'main_thread', index, mainthreads)
    saveFile(outdir, 'background_threads', index, backgroundthreads)
    for i, dim in enumerate(dimsinfo):
        field = dims[i]['field_name']
        dims[i]['allowed_values'] = list(dimvalues[i])
        saveFile(outdir, field, index['dimensions'], dim, prefix='dim_')

def processSessions(index, dims, sessionsfile, outdir):
    sessions = {}
    def stripval(k, v):
        ret = {x: y for x, y in v.iteritems()
                if x in allowed_infos[k]}
        ret[""] = sum(v.itervalues()) - sum(ret.itervalues())
        return ret
    for line in sessionsfile:
        parts = line.partition('\t')
        key = json.loads(parts[0])
        aggregate = {k: stripval(k, v) for k, v
                     in json.loads(parts[2]).iteritems()
                     if k in allowed_infos}
        sessions.setdefault(dims[key[0]]['field_name'],
            {'uptime': {}})['uptime'][key[1]] = aggregate
    for fieldname, sessionsvalue in sessions.iteritems():
        saveFile(outdir, fieldname,
            index['sessions'], sessionsvalue, prefix='ses_')

if __name__ == '__main__':

    from datetime import datetime, timedelta

    if len(sys.argv) != 3:
        print 'Usage %s <from> <to>' % (sys.argv[0])
        sys.exit(1)

    DATE_FORMAT = '%Y%m%d'
    fromDate = datetime.strptime(sys.argv[1], DATE_FORMAT)
    toDate = datetime.strptime(sys.argv[2], DATE_FORMAT)

    if toDate < fromDate:
        print 'To date is less than from date'
        sys.exit(1)

    mindate = fromDate.strftime(DATE_FORMAT)
    maxdate = toDate.strftime(DATE_FORMAT)
    workdir = os.path.join('/mnt', 'tmp-anr-%s-%s' % (mindate, maxdate))
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    sessionsdir = os.path.join('/mnt', 'tmp-sessions-%s-%s' % (mindate, maxdate))
    if not os.path.exists(sessionsdir):
        os.makedirs(sessionsdir)

    outdir = os.path.join('/mnt', 'anr-%s-%s' % (mindate, maxdate))
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    print 'Range: %s to %s' % (mindate, maxdate)
    print 'Work dir: %s' % workdir
    print 'Out dir: %s' % outdir

    dims = [{
        'field_name': 'reason',
        'allowed_values': ['android-anr-report']
    }, {
        'field_name': 'appName',
        'allowed_values': '*'
    }, {
        'field_name': 'appUpdateChannel',
        'allowed_values': '*'
    }, {
        'field_name': 'appVersion',
        'allowed_values': '*'
    }, {
        'field_name': 'appBuildID',
        'allowed_values': '*'
    }, {
        'field_name': 'submission_date',
        'allowed_values': {
            'min': mindate,
            'max': maxdate
        }
    }]

    index = {
        'dimensions': {},
        'sessions': {},
    }
    with tempfile.NamedTemporaryFile('r', suffix='.txt', dir=workdir) as outfile:
        runJob("mapreduce-dims.py", dims, workdir, outfile)
        with open(outfile.name, 'r') as jobfile:
            processDims(index, dims, jobfile, outdir)

    with tempfile.NamedTemporaryFile('r', suffix='.txt', dir=sessionsdir) as outfile:
        local = 'saved-session' in dims[0]['allowed_values']
        dims[0]['allowed_values'] = ['saved-session'];
        runJob("mapreduce-sessions.py", dims, sessionsdir, outfile, localonly=local)
        with open(outfile.name, 'r') as sessionsfile:
            processSessions(index, dims, sessionsfile, outdir)

    with open(os.path.join(outdir, 'index.json'), 'w') as outfile:
        outfile.write(json.dumps(index))

    print 'Completed'

