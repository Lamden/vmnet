const Component = (function(){
    function Component (parent, args={}){
        if (!args.id) args.id = args.id ? args.id : Util.dom_uuid();
        this.parent = $(parent);
        this.parent_id = parent;
        if (this.render) this.render(parent, args)
        else if (this.template) {
            if (args.replace) $(parent).html(this.template(args))
            else $(parent).append(this.template(args));
        }
        this.ele = $(`${parent} #${args.id}`);
        this.ele_id = `#${args.id}`;
        this.ele.addClass('component');
        this.args = this.args ? $.extend({},args) : args;
        this.metadata = args.metadata;
        this.class = args.class;
        this.components = [];
        if (args.data) this.data = args.data;
        if (args.class) this.ele.addClass(args.class);
        for (var function_name in Component.prototype)
            this.__proto__[function_name] = Component.prototype[function_name];
        if (this.add_components) this.add_components(parent, args);
        if (this.set_events) this.set_events();
    }
    Component.prototype.export_data = function() {
        if (this.data) {
            if (!this.error)
                return Util.lock_data(this.data);
        } else {
            var data = {};
            for (var i in this.components) {
                var component_data = this.components[i].export_data();
                var metadata = this.components[i].metadata;
                if (component_data && metadata) {
                    if (!data[metadata.key] && metadata.type == 'element')
                        data[metadata.key] = [];
                    switch (metadata.type) {
                        case 'element': data[metadata.key][this.components[i].ele.index()] = component_data; break;
                        case 'attribute': data[metadata.key] = component_data; break;
                    }
                }
            }
            if (!$.isEmptyObject(data))
                return Util.lock_data(data);
        }
    }
    return Component;
})();
