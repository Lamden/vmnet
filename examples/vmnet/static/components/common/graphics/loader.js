const Loader = (function(){
    function Loader (parent, args) {
        $(parent).append(`
            <div class="loader transition-delay icon xlarge">
                <img src="assets/img/icons/loader.svg">
            </div>
        `);
        Component.call(this, parent, args);
    }
    return Loader;
})();
