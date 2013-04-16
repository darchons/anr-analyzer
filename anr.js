"use strict";

function ANRReport(jsonObj) {
    jsonObj.__proto__ = ANRReport.prototype;
    return jsonObj;
}

ANRReport.getFrame = function (stack) {
    var parts = stack.split(':');
    if (!stack.startsWith('j')) {
        return parts.slice(2).join(':') + (parts[2] ? ' ' : '') +
            '(' + parts[1] + ')';
    }
    if (!parts[2]) {
        return parts[1];
    }
    return parts[1] + ' (line ' + parts[2] + ')';
}

ANRReport.arraymerge = function (first, second) {
    // from jQuery.merge
    var l = second.length,
        i = first.length,
        j = 0;
    for ( ; j < l; j++ ) {
        first[ i++ ] = second[ j ];
    }
    first.length = i;
    return first;
};

ANRReport.merge = function (left, right, key) {

    // left, right are array of array of ANRReport
    // returns array of array of ANRReport
    var leftLen = left.length;
    ANRReport.arraymerge(left, right);
    var ret = left;

    function mergeList(leftIndex, rightIndex) {
        if (ret[leftIndex][0].detail() >= ret[rightIndex][0].detail()) {
            ANRReport.arraymerge(ret[leftIndex], ret[rightIndex]);
            ret[rightIndex] = null;
            return leftIndex;
        } else {
            ANRReport.arraymerge(ret[rightIndex], ret[leftIndex]);
            ret[leftIndex] = null;
            return rightIndex;
        }
    }
    for (var i = leftLen; i < ret.length; ++i) {
        var node = ret[i];
        if (node === null || node.length == 0) {
            continue;
        }
        if (key(ret[0], node, ret[0][0].compare(node[0]))) {
            node.left = ret[0].left;
            node.right = ret[0].right;
            if (mergeList(0, i) !== 0) {
                ret[0] = ret[i];
                ret[i] = null;
            }
            continue;
        }
        (function treemerge(root) {
            if (root.left === undefined) {
                node.left = node.right = undefined;
                root.left = i;
                return;
            }
            var leftScore = ret[root.left][0].compare(node[0]);
            if (key(ret[root.left], node, leftScore)) {
                node.left = ret[root.left].left
                node.right = ret[root.left].right
                root.left = mergeList(root.left, i);
                return;
            }
            if (root.right === undefined) {
                node.left = node.right = undefined;
                root.right = i;
                return;
            }
            var rightScore = ret[root.right][0].compare(node[0]);
            if (key(ret[root.right], node, rightScore)) {
                node.left = ret[root.right].left
                node.right = ret[root.right].right
                root.right = mergeList(root.right, i);
                return;
            }
            if (leftScore >= rightScore) {
                treemerge(ret[root.left]);
            } else {
                treemerge(ret[root.right]);
            }
        })(ret[0]);
    }
    return ret;
};

ANRReport.cluster = function (list, key) {
    // list is array of ANRReport
    // returns array of array of ANRReport
    if (list.length == 1) {
        return [list];
    }
    var half = Math.floor(list.length / 2);
    return ANRReport.merge(
        ANRReport.cluster(list.slice(0, half), key),
        ANRReport.cluster(list.slice(half), key),
        key);
};

ANRReport.prototype = {
    // returns similarity [0.0, 1.0]
    compare: function (other) {
        return this._compareStack(this.main, other.main);
    },

    detail: function () {
        return this.main.length;
    },

    _compareStack: function (left, right) {
        // left and right are in the form
        // ['frame 0', 'frame 1', ...]
        if (left.length < right.length) {
            return this._compareStack(right, left);
        }
        for (var leftStart = 0; leftStart < left.length; ++leftStart) {
            if (left[leftStart].startsWith('j')) {
                break;
            }
        }
        for (var rightStart = 0; rightStart < right.length; ++rightStart) {
            if (right[rightStart].startsWith('j')) {
                break;
            }
        }
        return 1.0 - (this._compareStackRange(
                left.slice(leftStart), right.slice(rightStart)) /
            Math.max(left.length - leftStart, right.length - rightStart));
    },

    // performs DTW matching of two stack ranges and
    // returns a score representing dissimilarity
    _compareStackRange: function (left, right) {
        // left and right are in the form
        // ['frame 0', 'frame 1', ...]
        var column = new Array(left.length);
        var prevColumn = new Array(left.length);

        // first column
        column[0] = 1.0 - this._compareStackFrame(left[0], right[0]);
        for (var j = 1; j < left.length; ++j) {
            column[j] = column[j - 1] + 1.0 - this._compareStackFrame(left[j], right[0]);
        }
        // rest of the columns
        for (var i = 1; i < right.length; ++ i) {
            var tmp = prevColumn;
            prevColumn = column;
            column = tmp;
            column[0] = prevColumn[0] + 1.0 - this._compareStackFrame(left[0], right[i]);
            for (var j = 1; j < left.length; ++j) {
                column[j] = Math.min(prevColumn[j], prevColumn[j - 1], column[j - 1]) +
                    1.0 - this._compareStackFrame(left[j], right[i]);
            }
        }
        return column[column.length - 1];
    },

    _compareStackFrame: function (left, right) {
        // left and right are in the form
        // 'j:method:line' or 'c:lib:func'
        if (left.startsWith('c') || right.startsWith('c')) {
            throw 'native stack comparison not implemented!'
        }
        return this._compareJava(left.split(':'), right.split(':'));
    },

    _compareJava: function (left, right) {
        // left and right are in the form
        // ['j', method, line]
        return this._compareJavaMethod(left[1], right[1]);
    },

    // returns similarity [0.0, 1.0]
    _compareJavaMethod: function (left, right) {
        // left and right are in the form
        // 'pkg.cls$inner.method'
        if (!left.length || !right.length) {
            return 0.0;
        }
        if (left && right && left === right) {
            return 1.0;
        }
        function getParts(sig) {
            var methodIndex = sig.lastIndexOf('.');
            var clsIndex = sig.lastIndexOf('.', methodIndex - 1);
            var innerIndex = sig.indexOf('$', clsIndex);
            if (innerIndex == -1 || innerIndex > methodIndex) {
                innerIndex = methodIndex;
            }
            // return [pkg, cls, cls$inner, method]
            return [sig.slice(0, clsIndex),
                    sig.slice(clsIndex + 1, innerIndex),
                    sig.slice(clsIndex + 1, methodIndex),
                    sig.slice(methodIndex + 1)];
        }
        var leftParts = getParts(left), rightParts = getParts(right);
        if (leftParts[0] !== rightParts[0]) {
            return 0.0;
        }
        if (leftParts[1] !== rightParts[1]) {
            return 0.2;
        }
        return (leftParts[2] === rightParts[2] ? 0.1 : 0.0) +
               (leftParts[3] === rightParts[3] ? 0.4 : 0.0) + 0.5;
    }
};

