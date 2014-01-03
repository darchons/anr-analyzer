#!/usr/bin/python2

if __name__ == '__main__':

    import json, os, sys, tempfile
    from datetime import datetime, timedelta
    from fetchtelemetry import processBHR, runJob

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
    workdir = os.path.join('/mnt', 'tmp-bhr-%s-%s' % (mindate, maxdate))
    localonly = os.path.exists(os.path.join(workdir, 'cache'))
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    outdir = os.path.join('/mnt', 'bhr-%s-%s' % (mindate, maxdate))
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    print 'Range: %s to %s' % (mindate, maxdate)
    print 'Work dir: %s' % workdir
    print 'Out dir: %s' % outdir
    if localonly:
        print 'Local only'

    dims = [{
        'field_name': 'reason',
        'allowed_values': ['saved-session']
    }, {
        'field_name': 'appName',
        'allowed_values': '*'
    }, {
        'field_name': 'appUpdateChannel',
        'allowed_values': ['nightly', 'aurora']
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
        runJob("bhr.py", dims, workdir, outfile.name, local=localonly)
        with open(outfile.name, 'r') as jobfile:
            processBHR(index, jobfile, outdir)

    runJob("mapreduce-summary.py", dims, workdir,
           os.path.join(outdir, 'summary.txt'), local=True)

    with open(os.path.join(outdir, 'index.json'), 'w') as outfile:
        outfile.write(json.dumps(index))

    print 'Completed'

