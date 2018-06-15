const Terminal = (function(){
    function Terminal (parent, args={}) {
        Component.call(this, parent, args);
        this.auto_scroll_to_bottom = true;
    }
    Terminal.prototype.template = function(args) {
        return `
            <div id="${args.id}" class="terminal-wrapper">
                <div class="tab-title">${args.tab_title}</div>
                <div class="terminal"></div>
            </div>
        `
    }
    Terminal.prototype.set_events = function () {
        $(this.ele).on('add_lines', function(e, data){
            console.log(data);
            var terminal = $(this.ele).find('.terminal');
            terminal.append(`<div>${data}</div>`);
            if (this.auto_scroll_to_bottom) {
                terminal.scrollTop(terminal[0].scrollHeight);
            }
        }.bind(this));
        $(this.ele).find('.terminal').scroll(function(){
            var terminal = $(this.ele).find('.terminal');
            this.auto_scroll_to_bottom = terminal.scrollTop() > terminal[0].scrollHeight-terminal.height()-50;
        }.bind(this));
        $(this.ele).find('.tab-title').on('click', function(){
            $(this).parent().toggleClass('full-screen');
        });
    }

    return Terminal;

})();
