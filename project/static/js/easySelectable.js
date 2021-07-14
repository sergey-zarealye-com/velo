/*
Author: mee4dy@gmail.com
*/
selected_items_set = new Set();
selected_items_el = new Set();
options = null;
(function ($) {
    //selectable html elements
    $.fn.easySelectable = function (options_) {
        var el = $(this);
        options = $.extend({
            'item': 'li',
            'state': true,
            onSelecting: function (el) {

            },
            onSelected: function (el) {

            },
            onUnSelected: function (el) {

            }
        }, options_);
        el.on('dragstart', function (event) {
            event.preventDefault();
        });
        el.off('mouseover');
        el.addClass('easySelectable');
        if (options.state) {
            el.find(options.item).addClass('es-selectable');
            el.on('mousedown', options.item, function (e) {
                $(this).trigger('start_select');
                var offset = $(this).offset();
                // var hasClass = $(this).hasClass('es-selected');
                var hasSelect = $(this).data("has-select");
                var prev_el = false;
                el.on('mouseover', options.item, function (e) {
                    if (prev_el == $(this).index()) return true;
                    prev_el = $(this).index();
                    var hasClass2 = $(this).data("has-select");

                    $(this).removeClass('es-unselected-has-class').
                            removeClass('es-selected-no-class').
                            removeClass('es-unselected-has-class').
                            removeClass('es-selected-has-class')

                    if (!hasClass2) {
                        if ($(this).data("has-class")){
                            $(this).addClass('es-selected-has-class').
                                    trigger('selected');
                        } else {
                            $(this).addClass('es-selected-no-class').
                                    trigger('selected');
                        }
                        $(this).data("has-select",true)
                        el.trigger('selected');
                        options.onSelecting($(this));
                        options.onSelected($(this));
                        selected_items_set.add({"li": $(this), "div": el});
                        update_selected_items_text();
                    } else {
                        if ($(this).data("has-class")){
                            $(this).addClass('es-unselected-has-class').
                                    trigger('unselected');
                        } else {
                            $(this).addClass('es-unselected-no-class').
                                    trigger('unselected');
                        }
                        $(this).data("has-select",false)
                        el.trigger('unselected');
                        options.onSelecting($(this))
                        options.onUnSelected($(this));
                        selected_items_set.delete({"li": $(this), "div": el});
                        selected_items_set.forEach((item) => {
                          if (item["li"][0].id == $(this)[0].id) {
                            selected_items_set.delete(item);
                          }
                        });
                        update_selected_items_text();
                    }
                });
                $(this).removeClass('es-unselected-has-class').
                    removeClass('es-selected-no-class').
                    removeClass('es-unselected-has-class').
                    removeClass('es-selected-has-class')
                if (!hasSelect) {
                    prev_el = $(this).index();
                    if ($(this).data("has-class")){
                        $(this).addClass('es-selected-has-class').
                                trigger('selected');
                    } else {
                        $(this).addClass('es-selected-no-class').
                                trigger('selected');
                    }
                    $(this).data("has-select",true)
                    el.trigger('selected');
                    options.onSelecting($(this));
                    options.onSelected($(this));
                    selected_items_set.add({"li": $(this), "div": el});
                    update_selected_items_text();
                } else {
                    prev_el = $(this).index();
                    if ($(this).data("has-class")){
                        $(this).addClass('es-unselected-has-class').
                                trigger('unselected');
                    } else {
                        $(this).addClass('es-unselected-no-class').
                                trigger('unselected');
                    }
                    $(this).data("has-select",false)
                    el.trigger('unselected');
                    options.onSelecting($(this));
                    options.onUnSelected($(this));
                    selected_items_set.forEach((item) => {
                          if (item["li"][0].id == $(this)[0].id) {
                            selected_items_set.delete(item);
                          }
                        });
                    update_selected_items_text();
                }
                var relativeX = (e.pageX - offset.left);
                var relativeY = (e.pageY - offset.top);
            });
            $(document).on('mouseup', function () {
                el.off('mouseover');
            });
        } else {
            el.off('mousedown');
        }
    };

    $(document).ready(function () {
        $('#easySelectable').easySelectable();

        $('[id^="class_id_"]').click(function () {
            selected_items_set.forEach((item) => {
                document.getElementById('text_class_' + item["li"][0].id).innerHTML = $(this).val();
                item["li"].data("has-class",true)
                item["li"].data("has-select",false)
                item["li"].removeClass('es-selected').trigger('unselected');
                item["li"].removeClass('es-selected-has-class').trigger('unselected');
                item["li"].addClass('es-unselected-has-class').trigger('selected');
                item["div"].trigger('unselected');
                options.onSelecting(item["li"]);
                options.onUnSelected(item["li"]);
            });
            selected_items_set.clear();
            update_selected_items_text();
            $(this).prop( "checked", false );
        });
    })

    function update_selected_items_text() {
        $('#selected_items_amount').html("Selected (" + selected_items_set.size + ")");
        var str = ''
        selected_items_set.forEach((item) => {
            str += item["li"][0].id + '\n'
        });
        $('#selected_items_list').html(str);
    }


    function handleClick(el) {
        console.log("click")
    }
})(jQuery);
