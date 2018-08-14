const Input = (function(){
    function Input (parent, args) {
        this.sanitize = args.sanitize == undefined ? true : args.sanitize;
        this.data = args.text;
        Component.call(this, parent, args);
    }
    Input.prototype.template = function(args) {
        const transition_delay = 'transition-delay';
        const icon_html = args.icon ? `<img class="input-icon ${transition_delay}" src="${args.icon}"/>` : '';
        const input_class = args.icon ? 'input input-with-icon' : 'input';
        const placeholder_html = args.placeholder ? `<div class="placeholder ${transition_delay}">${args.placeholder}</div>` : '';
        const value_html = args.text ? args.text : '';
        const type_html = args.type ? args.type : 'text';
        return `
            <div id="${args.id}" class="${input_class} ${transition_delay}">
                <input
                    value="${value_html}"
                    type="${type_html}"
                    class="${transition_delay}"
                />
                ${placeholder_html}
                ${icon_html}
                <div class="error ${transition_delay}"></div>
            </div>
        `;
    }
    Input.prototype.set_events = function () {
        $(this.ele).find('input')
            .keyup(function(e){
                var input = $(this.ele).find('input');
                if ($.trim(input.val()) != '')
                    $(this.ele).find('.placeholder').addClass('has-text')
                else
                    $(this.ele).find('.placeholder').removeClass('has-text')
            }.bind(this))
            .on('check_input', check_inputs.bind(this))
            .blur(check_inputs.bind(this));
        function check_inputs (e) {
            this.sanitize_input();
            var input = $(e.target);
            var password = $(this.parent).find('#password input');
            switch (this.args.check) {
                case 'email': this.check_email(input.val()); break;
                case 'password': this.check_password(input.val()); break;
                case 'confirm': this.check_confirm(input.val(),password.val()); break;
            }
            this.data = input.val();
        }
    }

    Input.prototype.sanitize_input = function () {
        var input = $(this.ele).find('input');
        input.val(HTMLSanitizer.sanitizeString(input.val()));
    }
    Input.prototype.display_error = function (error) {
        this.error = true;
        $(this.ele).find('.error').text(error).addClass('show');
    }
    Input.prototype.hide_error = function () {
        this.error = false;
        $(this.ele).find('.error').text('').removeClass('show');
    }
    Input.prototype.check_email = function (str) {
        const ERROR = app.consts.pages.login_page.errors.inputs;
        const regex = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/g;
        if (!regex.test(str))
            this.display_error(ERROR.invalid_email);
        else this.hide_error();
    }
    Input.prototype.check_password = function (str) {
        const ERROR = app.consts.pages.login_page.errors.inputs;
        const regex = this.args.special_chars ?
            /(?=.*?\d)(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[\~\`\!\@\#\$\%\^\&\*\(\)\-\+\=])[A-Za-z\d\~\`\!\@\#\$\%\^\&\*\(\)\-\+\=]{8,}/g :
            /(?=.*?\d)(?=.*?[A-Z])(?=.*?[a-z])[A-Za-z\d]{8,}/g;
        if (!regex.test(str))
            this.display_error(this.args.special_chars ?
                ERROR.invalid_password_special_chars :
                ERROR.invalid_password
            );
        else this.hide_error();
    }
    Input.prototype.check_confirm = function (str1,str2) {
        const ERROR = app.consts.pages.login_page.errors.inputs;
        if ((str1 || str2) && str1 != str2)
            this.display_error(ERROR.password_not_match);
        else this.hide_error();
    }
    return Input;
})();
