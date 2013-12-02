#!/usr/bin/python2

import json

if __name__ == '__main__':

    import os, sys, subprocess, tempfile
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

    print 'Processing %s...' % (str(fromDate.date()))

    mindate = fromDate.strftime(DATE_FORMAT)
    maxdate = toDate.strftime(DATE_FORMAT)
    filterfile = tempfile.NamedTemporaryFile('w', suffix='.json')
    filterfile.write(json.dumps({
        'version': 1,
        'dimensions': [{
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
    }))
    filterfile.flush()

    args = ['python', '-m', 'mapreduce.job',
            os.path.join(os.path.dirname(sys.argv[0]), 'mapreduce.py'),
            '--input-filter', filterfile.name,
            '--num-mappers', '16',
            '--num-reducers', '4',
            '--data-dir', '/mnt/telemetry/work',
            '--work-dir', '/mnt/telemetry/work',
            '--output', '/mnt/telemetry/anr-%s-%s.txt' % (mindate, maxdate),
            '--bucket', 'telemetry-published-v1']

    env = os.environ
    print 'Calling %s' % (str(' '.join(args)))
    ret = subprocess.call(args, env=env)
    if ret:
        print 'Error %d' % (ret)
        sys.exit(ret)

    print 'Completed'

