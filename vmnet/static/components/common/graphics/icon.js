const Icon = (function(){
    function Icon (parent, args) {
        this.data = args.icon;
        Component.call(this, parent, args);
    }
    Icon.prototype.template = function(args) {
        const type = args.type ? args.type : 'small';
        const clickable = args.clickable ? 'clickable' : '';
        return `
            <div id="${args.id}" class="icon ${type} ${clickable} transition-delay">
                <img src="${args.icon}"/>
            </div>
        `;
    }
    return Icon;
})();
