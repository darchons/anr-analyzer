#!/usr/bin/python2

import gzip, os, json, subprocess, sys, tempfile

def runJob(mindate, maxdate, dims, workdir, outfile):
    with tempfile.NamedTemporaryFile('w', suffix='.json') as filterfile:
        filterfile.write(json.dumps({
            'version': 1,
            'dimensions': dims
        }))
        filterfile.flush()

        args = ['python', '-m', 'mapreduce.job',
                os.path.join(os.path.dirname(sys.argv[0]), 'mapreduce.py'),
                '--input-filter', filterfile.name,
                '--num-mappers', '16',
                '--num-reducers', '4',
                '--data-dir', workdir,
                '--work-dir', workdir,
                '--output', outfile.name,
                '--bucket', 'telemetry-published-v1']

        env = os.environ
        print 'Calling %s' % (str(' '.join(args)))
        ret = subprocess.call(args, env=env)
        if ret:
            print 'Error %d' % (ret)
            sys.exit(ret)

def processJob(dims, jobfile, outdir):
    index = {
        'dimensions': {},
    }
    mainthreads = {}
    backgroundthreads = {}
    slugs = {}
    dimsinfo = [{} for i in range(len(dims))]
    for line in jobfile:
        anr = json.loads(line.partition('\t')[2])
        slug = anr['slugs'][0]
        slugs[slug] = anr['slugs']
        mainthreads[slug] = anr['threads'][0]
        backgroundthreads[slug] = anr['threads'][1:]
        info = anr['info']
        for i, infocounts in enumerate(info):
            for key, value in infocounts.iteritems():
                dimsinfo[i].setdefault(slug, {})[key] = value

    def saveFile(name, index, data):
        fn = name + '.json'
        with gzip.open(os.path.join(outdir, fn + '.gz'), 'wb') as outfile:
            outfile.write(json.dumps(data))
        index[name] = fn

    saveFile('slugs', index, slugs)
    saveFile('main_thread', index, mainthreads)
    saveFile('background_threads', index, backgroundthreads)
    for i, dim in enumerate(dimsinfo):
        field = dims[i]['field_name']
        saveFile(field, index['dimensions'], dim)
    with open(os.path.join(outdir, 'index.json'), 'w') as outfile:
        outfile.write(json.dumps(index))

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
    workdir = tempfile.mkdtemp()
    outdir = os.path.join(tempfile.gettempdir(), 'anr-%s-%s' % (mindate, maxdate))
    try:
        os.makedirs(outdir)
    except OSError:
        pass

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

    with tempfile.NamedTemporaryFile('r', suffix='.txt') as outfile:
        runJob(fromDate.strftime(DATE_FORMAT),
               toDate.strftime(DATE_FORMAT),
               dims, workdir, outfile)
        with open(outfile.name, 'r') as jobfile:
            processJob(dims, jobfile, outdir)

    print 'Completed'

