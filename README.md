ANR Report Analyzer
===================

Scripts to parse and analyze ANR reports

## anr.py

Parses ANR reports from the input file and groups them into similar reports, based on a threshold value.

Each line of the input file is an ANR report in JSON format (see ANRReporter.java).

The threshold value from 0.0 to 1.0 indicates how similar reports have to be in order to be grouped together; 0.0 indicates two reports are totally distinct, and 1.0 indicates two reports are identical. In practice, unrelated reports have similarity of around 0.3 and below, and related reports have similarity of around 0.7 and above; a good starting threshold is around 0.6.

#### Usage

    python anr.py <threshold> <input>

      <threshold>     grouping threshold from 0.0 to 1.0
      <input>         input file of ANR reports

