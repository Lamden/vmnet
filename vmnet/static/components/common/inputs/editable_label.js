const EditableLabel = (function(){
    function EditableLabel (parent, args) {
        this.data = args.text;
        this.no_click_text = args.no_click_text;
        Component.call(this, parent, args);
    }
    EditableLabel.prototype.add_components = function (parent, args) {
        if (!args.no_icon) {
            this.components.push(new Icon(`${parent} #${args.id}`, {
                class: 'edit-icon',
                type: 'xsmall',
                icon: 'assets/img/icons/edit.png'
            }))
        }
    }
    EditableLabel.prototype.template = function (args) {
        const text = args.text ? args.text : '';
        return `
            <div id="${args.id}" class="editable-label">
                <span class="text">${text}</span>
                <div class="edit">
                    <input type="text" value="${text}"/>
                </div>
            </div>
        `;
    }
    EditableLabel.prototype.set_events = function () {
        var edit_classes = this.no_click_text ? '.edit-icon' : '.text,.edit-icon';
        $(this.ele).find(edit_classes).on('click', function(e){
            this.make_edit();
        }.bind(this));
        $(this.ele).find('.edit input').on('keyup', function(e){
            if (e.keyCode == 13) this.save_changes();
        }.bind(this))
            .blur(this.save_changes.bind(this))
    }

    EditableLabel.prototype.make_edit = function () {
        $(this.ele).find('.text,.edit-icon').hide();
        $(this.ele).find('.edit').show();
        $(this.ele).find('.edit input').select();
    }

    EditableLabel.prototype.save_changes = function () {
        this.sanitize_input();
        var new_text = $(this.ele).find('.edit input').val();
        $(this.ele).find('.text').text(new_text)
        $(this.ele).find('.text,.edit-icon').show();
        $(this.ele).find('.edit').hide();
        this.data = new_text;
    }

    EditableLabel.prototype.sanitize_input = function () {
        var input = $(this.ele).find('.edit input');
        input.val(HTMLSanitizer.sanitizeString(input.val()));
    }
    return EditableLabel;
})();
