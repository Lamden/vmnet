var app = {};
const debug = true;
const WS_PORT = 4321;

$(document).ready(function(){
    if (debug) $.ajaxSetup({ cache: false });
    Util.load_consts('en').then(function(json){
        app.consts = json;
        (function(){
            app.page = new Console();
        })();
    });
});
