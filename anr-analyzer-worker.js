/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var ANR_PLOT_LIMIT = 15;

onmessage = function (aEvent) {

    var anrLists = aEvent.data['lists'];
    var version = aEvent.data['version'];

    importScripts('anr.js');
    anrLists.forEach(function (list) {
        list.forEach(function (anr) {
            anr.__proto__ = ANRReport.prototype;
            anr.preprocess();
        });
    });

    function key(left, right, score) {
        var leftVersion = (left[0]['info']['appVersion'] === version);
        var rightVersion = (right[0]['info']['appVersion'] === version);
        if (!leftVersion && !rightVersion) {
            // group reports of other versions together
            return true;
        }
        return leftVersion && rightVersion && score >= 0.7;
    }
    // clusters of ANR reports
    var clusters = ANRReport.cluster(anrLists[0], key);
    for (var i = 1; i < anrLists.length; ++i) {
        clusters = ANRReport.merge(clusters,
            ANRReport.cluster(anrLists[i], key), key);
    }
    clusters = clusters.filter(function (list) {
        return list !== null && list[0]['info']['appVersion'] === version;
    }).sort(function (left, right) {
        function sum(prevVal, elem) {
            return prevVal + elem['count'];
        }
        return left.reduce(sum, 0) - right.reduce(sum, 0);
    });
    for (var i = clusters.length - ANR_PLOT_LIMIT - 1; i >= 0; --i) {
        ANRReport.arraymerge(clusters[clusters.length - ANR_PLOT_LIMIT], clusters[i]);
        clusters[clusters.length - ANR_PLOT_LIMIT].isOther = true;
    }
    clusters = clusters.splice(-ANR_PLOT_LIMIT);
    clusters.compareCount = ANRReport.compareCount;

    postMessage(clusters);
    self.close();
}
