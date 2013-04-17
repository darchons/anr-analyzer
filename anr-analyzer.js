
"use strict";

// Vars from query or hash in form #key[:val],...
var gQueryVars = (function () {
  var ret = {};
  function expand(target, outer, inner) {
    var vars = target.split(outer);
    for (var x in vars) {
      x = vars[x].split(inner);
      ret[decodeURIComponent(x[0]).toLowerCase()] = x.length > 1 ? decodeURIComponent(x[1]) : true;
    }
  }
  if (document.location.search)
    expand(document.location.search.slice(1), '&', '=')
  if (document.location.hash)
    expand(document.location.hash.slice(1), ',', ':')
  return ret;
})();

var STACK_LIMIT = 15;

var gANRLists = [], gANRVersions;
var gANRBuilds, gANRBuildTimes;
var gANRSubmits, gANRSubmitTimes;

function generateChart(clusters, options) {
    var graph = options['graph'],
        colors = options['colors'],
        indexName = options['index'] || 'appBuildID';
    var indexList = {'appBuildID': gANRBuilds,
                     'submitted': gANRSubmits}[indexName],
        indexAxis = {'appBuildID': gANRBuildTimes,
                     'submitted': gANRSubmitTimes}[indexName],
        indexLabel = {'appBuildID': 'Build ID',
                      'submitted': 'Submitted'}[indexName];
    // data for plot
    var data = [],
        totalCount = {};
    for (var i = 0; i < clusters.length; ++i) {
        var clus = clusters[i],
            series = {};
        for (var j = 0; j < clus.length; ++j) {
            var index = clus[j]['info'][indexName];
            var count = clus[j]['count'];
            series[index] = (series[index] || 0) + count;
            totalCount[index] = (totalCount[index] || 0) + count;
        }
        data.push(indexList.map(function (val) {
            return [val, series[val] || 0];
        }));
    }
    data = data.map(function (series) {
        return series.filter(function (point) {
            return point[0] in totalCount;
        });
    });
    var plotdata = data.map(function (series) {
        return series.map(function (point) {
            return [indexAxis[point[0]], point[1]];
        });
    });
    var plot = $.plot(graph, plotdata, {
        series: {
            stack: true,
            lines: {
                show: true,
                fill: true
            },
            points: {
                show: true
            }
        },
        grid: {
            hoverable: true,
            clickable: true
        },
        xaxis: {
            mode: 'time',
            timeformat: '%m/%d'
        },
        yaxis: {
            minTickSize: 1
        },
        colors: colors
    });

    function getNonEmptySeries(item) {
        var series = item.seriesIndex;
        if (item.datapoint[1] == item.datapoint[2]) {
            for (; series > 0; --series) {
                if (data[series][item.dataIndex][1] != 0) {
                    break;
                }
            }
        }
        return series;
    }

    var prevItem = null;
    graph.unbind("plothover");
    graph.bind("plothover", function (event, pos, item) {
        if (item) {
            if (item.datapoint.toString() !== prevItem) {
                prevItem = item.datapoint.toString();
                var series = getNonEmptySeries(item),
                    cluster = clusters[series],
                    tooltip = $('#tooltip'),
                    index = data[series][item.dataIndex][0],
                    count = data[series][item.dataIndex][1],
                    total = totalCount[index];
                $('#tooltip-label').text(indexLabel);
                $('#tooltip-value').text(index);
                $('#tooltip-count').text(count);
                $('#tooltip-percent').text(Math.round(100 * (total ? count / total : 1)));
                $('#tooltip-stack').text((function () {
                    if (cluster.isOther) {
                        return 'Other ANRs'; // 'other' category
                    }
                    return cluster[0].main.filter(function (val) {
                        return !val.startsWith('c');
                    }).splice(0, STACK_LIMIT).map(function (val) {
                        return val.split(':')[1];
                    }).join('\n');
                })());
                tooltip.css('background-color', colors[colors.length - 1]);
                tooltip.css('border-color', colors[colors.length - 1]);
                var l = item.pageX,
                    t = item.pageY,
                    off = graph.offset();
                l = l <= (off.left + graph.width() / 2) ?
                    l + 5 : l - tooltip.outerWidth() - 5;
                t = t <= (off.top + graph.height() / 2) ?
                    t + 5 : t - tooltip.outerHeight() - 5;
                tooltip.offset({left: l, top: t});
                tooltip.css('visibility', 'visible');
                tooltip.stop(true).animate({opacity: 1}, 200);
            }
        } else if (prevItem !== null) {
            prevItem = null;
            $('#tooltip').stop(true).animate({opacity: 0}, {
                duration: 200,
                complete: function () {
                    if (prevItem === null) {
                        $('#tooltip').css('visibility', 'hidden');
                    }
                }
            });
        }
    });
    graph.unbind("mouseout");
    graph.bind("mouseout", function (event) {
        graph.trigger('plothover', [event, null, null]);
    });

    $('#reports-close div').click(function () {
        $('#reports-popup').fadeOut(200);
    }).css('background-color', colors[colors.length - 1]);
    graph.unbind("plotclick");
    graph.bind("plotclick", function (event, pos, item) {
        if (!item) {
            return;
        }
        var series = getNonEmptySeries(item),
            cluster = clusters[series],
            reports = $('#reports'),
            template = $('#report-template');
        cluster = cluster.sort(function (left, right) {
            var leftIndex = left['info'][indexName],
                rightIndex = right['info'][indexName];
            if (leftIndex !== rightIndex) {
                return leftIndex < rightIndex ? -1 : 1;
            }
            return ['appBuildID', 'submitted'].reduce(function (prev, index) {
                if (prev) {
                    return prev;
                }
                leftIndex = left['info'][index];
                rightIndex = right['info'][index];
                if (leftIndex !== rightIndex) {
                    return leftIndex < rightIndex ? -1 : 1;
                }
                return 0;
            }, 0);
        });
        reports.children().not(template).remove();
        cluster.forEach(function (anr) {
            var report = template.clone().removeAttr('id');
            report.find('.report-count').text(
                (anr['count'] > 1 ? '(' + anr['count'] + ' duplicates)' : ''));
            report.find('.report-build').text(
                anr['info']['appBuildID']);
            report.find('.report-submitted').text(
                anr['info']['submitted']);
            var infolist = report.find('.report-info');
            for (var infokey in anr['info']) {
                infolist.append($('<li/>').text(
                    infokey + ': ' + anr['info'][infokey]));
            }
            var main = report.find('.report-main');
            anr['main'].forEach(function (stack) {
                main.append($('<li/>').text(
                    ANRReport.getFrame(stack)
                ).css('color', stack.startsWith('j') ? '': '#888'));
            })
            var threadTemplate = report.find('.report-threads');
            anr['threads'].forEach(function (thread) {
                var threadItem = threadTemplate.clone(),
                    threadStack = threadItem.children('.report-thread');
                thread['stack'].forEach(function (stack) {
                    threadStack.append($('<li/>').text(
                        ANRReport.getFrame(stack)
                    ).css('color', stack.startsWith('j') ? '': '#888'));
                })
                threadItem.children('.report-name').hover(function () {
                    $(this).css('background-color', colors[1]);
                }, function () {
                    $(this).css('background-color', colors[0]);
                }).click(function () {
                    threadStack.slideToggle(200);
                }).text(thread['name']);
                threadItem.show();
                threadStack.hide();
                report.children('ul').append(threadItem);
            });
            report.show();
            report.css('border-color', colors[colors.length - 1]);
            report.css('background-color', colors[colors.length - 1]);
            report.children('div').hover(function () {
                report.css('background-color', colors[colors.length - 2]);
            }, function () {
                report.css('background-color', colors[colors.length - 1]);
            }).click(function () {
                report.children('ul').slideToggle(200);
            });
            report.find('.report-name').css('background-color', colors[0]);
            report.children('ul').hide();
            reports.append(report);
        });
        reports.css('border-color', colors[colors.length - 1]);
        reports.css('background-color', colors[colors.length - 1]);
        $('#reports-popup').fadeIn(200);
    });
}

function refreshGraph(version, index) {

    $('#reports-popup').fadeOut(200);
    $('#throbber').fadeIn(500);
    if (gANRLists.length == 0) {
        $('#loading').text("There is no data! There is only XU... uh nevermind");
        return;
    }

    $('#loading').text('Processing data...');
    var dataWorker = new Worker('anr-analyzer-worker.js');
    dataWorker.postMessage({
        lists: gANRLists,
        version: version
    });

    dataWorker.onmessage = function (aEvent) {
        $('#loading').text('Generating chart...');
        var colors;
        if (version.endsWith('a1')) {
            colors = ['#A3B2CC', '#99ACCC', '#8FA5CC', '#859FCC', '#7A99CC',
                      '#7092CC', '#668CCC', '#5C85CC', '#527FCC', '#4779CC',
                      '#3D72CC', '#336CCC', '#2965CC', '#1F5FCC', '#1458CC'];
        } else if (version.endsWith('a2')) {
            colors = ['#B3A3CC', '#AD99CC', '#A78FCC', '#A185CC', '#9A7ACC',
                      '#9470CC', '#8E66CC', '#885CCC', '#8152CC', '#7B47CC',
                      '#753DCC', '#6F33CC', '#6929CC', '#621FCC', '#5C14CC'];
        } else {
            colors = ['#CCB2A3', '#CCAC99', '#CCA68E', '#CC9F84', '#CC997A',
                      '#CC9370', '#CC8D66', '#CC865B', '#CC8051', '#CC7A47',
                      '#CC733D', '#CC6D32', '#CC6728', '#CC611E', '#CC5A14'];
        }
        // window.alert('Comparisons: ' + aEvent.data.compareCount);
        generateChart(aEvent.data, {
            graph: $('.graph').first(),
            colors: colors,
            index: index
        });
        $('#throbber').fadeOut(500);
        $('#versions li a').each(function (i, elem) {
            $(this).css('border-bottom-color',
                !$(this).attr('href').endsWith(version) ? '' :
                version.endsWith('a1') ? '#B8C9E6' :
                version.endsWith('a2') ? '#CAB8E6' :
                                         '#E6AE8A');
        });
        $('#index li a').each(function (i, elem) {
            $(this).css('border-bottom-color',
                $(this).attr('href').endsWith(index) ? '#B0B0B0' : '');
        });
    };
}

$(function () {
    function getInfo(key) {
        var ret = [];
        for (var i = 0; i < gANRLists.length; ++i) {
            var file = gANRLists[i];
            for (var j = 0; j < file.length; ++j) {
                if (file[j]['info'][key] &&
                    $.inArray(file[j]['info'][key], ret) === -1) {
                    ret.push(file[j]['info'][key]);
                }
            }
        }
        ret.sort();
        return ret;
    }
    function filesLoaded() {
        gANRVersions = getInfo('appVersion');
        gANRVersions.reverse();

        var version = gANRVersions[0],
            index = 'submitted';

        gANRVersions.forEach(function (val) {
            $('#versions').append($('<li/>').append($('<a/>', {
                href: '#v' + val,
                text: val
            }).click(function () {
                version = $(this).attr('href').slice(2);
                refreshGraph(version, index);
            })));
        });
        ['appBuildID', 'submitted'].forEach(function (val) {
            $('#index').append($('<li/>').append($('<a/>', {
                href: '#' + val,
                text: {
                    'appBuildID': 'By build',
                    'submitted': 'By date'
                }[val]
            }).click(function () {
                index = $(this).attr('href').slice(1);
                refreshGraph(version, index);
            })));
        });
        gANRBuilds = getInfo('appBuildID');
        gANRBuildTimes = {};
        for (var i = 0; i < gANRBuilds.length; ++i) {
            gANRBuildTimes[gANRBuilds[i]] =
                Date.parse(gANRBuilds[i].replace(
                /^(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)$/,
                '$1-$2-$3T$4:$5:$6'));
        }
        gANRSubmits = getInfo('submitted');
        gANRSubmitTimes = {};
        for (var i = 0; i < gANRSubmits.length; ++i) {
            gANRSubmitTimes[gANRSubmits[i]] =
                Date.parse(gANRSubmits[i].replace(
                /^(\d\d\d\d)-(\d\d)-(\d\d)$/,
                '$1-$2-$3'));
        }
        $('.graph').each(function (index, elem) {
            $.plot($(elem), [[0, 0]]);
        });
        refreshGraph(version, index);
    }
    window.setTimeout(function () {
        var files = gQueryVars['files'].split(',');
        var completed = 0;
        for (var i = 0; i < files.length; ++i) {
            var file = files[i];
            $.ajax({
                url: (file.indexOf('/') >= 0 ?
                    'https://intranet.mozilla.org/images/' : '') + file,
                dataType: 'jsonp',
                cache: true,
                jsonp: false,
                jsonpCallback: file.slice(file.lastIndexOf('/') + 1,
                    file.lastIndexOf('.')).replace('-', '_', 'g').toLowerCase(),
                success: function (anrList) {
                    gANRLists.push(anrList);
                },
                complete: function () {
                    if ((++completed) == files.length) {
                        filesLoaded();
                    }
                }
            });
        }
    }, 100);
});

