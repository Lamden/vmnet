const Console = (function(){
    function Console (parent='#app') {
        Component.call(this, parent, { id:'console', replace: true });
    }
    Console.prototype.add_components = function (parent, args) {
        this.components = []
    }
    Console.prototype.template = function(args) {
        return `
            <style>
                #console {
                    height: 100vh;
                    overflow: auto;
                    background: rgb(50,50,50);
                }
            </style>
            <div id="console">
            </div>
        `
    }
    Console.prototype.set_events = function () { var self = this;
        this.ws = new WebSocket(`ws://localhost:${WS_PORT}`),
        this.ws.onmessage = function (event) {
            var data = JSON.parse(event.data);
            var node = data.node_num ? `${data.node_type}_${data.node_num}` : data.node_type;
            if (!$(`#${node}`).length) {
                new Terminal(`#console`, {id: node, tab_title: node});
            }
            $(`#${node}`).trigger('add_lines', [data.log_lines]);
            $(self.ele).find('.terminal-wrapper').sort(function (a, b) {
                return a.id > b.id;
            }).each(function (idx) {
                if ($(this).index() == idx) return;
                $(this).appendTo(self.ele);
            });
        };
        this.ws.onclose = function (event) {
            $(`.terminal-wrapper`).trigger('add_lines', [`<br><span class="msg">The test is complete!</span>`]);
        }
    }
    return Console;
})();
