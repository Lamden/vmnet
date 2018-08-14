const Util = (function(){
    var long_wait = undefined;
    var Util = Object.freeze({
        is_mobile: function () {
            return (navigator.userAgent.match(/Android/i)
                    || navigator.userAgent.match(/webOS/i)
                    || navigator.userAgent.match(/iPhone/i)
                    || navigator.userAgent.match(/iPad/i)
                    || navigator.userAgent.match(/iPod/i)
                    || navigator.userAgent.match(/BlackBerry/i)
                    || navigator.userAgent.match(/Windows Phone/i));
        },
        timezone: function () {
            return new Date().toString().split("GMT")[1].split(" (")[0];
        },
        load_consts: function (language) {
            return new Promise(function(resolve,reject){
                $.getJSON(`assets/lang/${language}.json`,function(json){
                    resolve(json);
                });
            })
        },
        guid: function () {
            function s4() {
                return Math.floor((1 + Math.random()) * 0x10000)
                    .toString(16)
                    .substring(1);
            }
            return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
        },
        dom_uuid: function () {
            var id = Util.guid();
            while ($(`#${id}`).length != 0) id = Util.guid();
            return id;
        },
        array_move: function (arr, old_index, new_index) {
            if (new_index >= arr.length) {
                var k = new_index - arr.length + 1;
                while (k--) {
                    arr.push(undefined);
                }
            }
            arr.splice(new_index, 0, arr.splice(old_index, 1)[0]);
            return arr;
        },
        lock_data: function (data) {
            Object.freeze(data);
            Object.preventExtensions(data);
            Object.seal(data);
            return data;
        },
        show_loader: function (reject, wait_time=3000) {
            $('body > .loader').addClass('loading');
            long_wait = setTimeout(function(){
                this.hide_loader();
                reject('This feature timed out!')
            }.bind(this), wait_time);
        },
        hide_loader: function () {
            clearTimeout(long_wait);
            $('body > .loader').removeClass('loading');
        }
    })
    return Util;
})();
