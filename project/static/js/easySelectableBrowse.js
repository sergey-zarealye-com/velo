/*
Author: mee4dy@gmail.com
*/
selected_items_set = new Set();
moderated_items_set = {};
options = null;
(function ($) {
    var es_unselected_no_class = "border-secondary";
    var es_selected_no_class = "bg-primary";
    var es_unselected_has_class = "border-success";
    var es_selected_has_class = "bg-warning";
    var es_unselected_has_class_del = "border-danger";
    var es_selected_has_class_del = "bg-danger";
    var all_cards_classes = [es_unselected_no_class,
                        es_selected_no_class,
                        es_unselected_has_class,
                        es_selected_has_class,
                        es_unselected_has_class_del,
                        es_selected_has_class_del]

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
            // $( ".selectable-item" ).addClass('es-selectable');
            el.on('mousedown', options.item, function (e) {
                $(this).trigger('start_select');
                var offset = $(this).offset();
                // var hasClass = $(this).hasClass('es-selected');
                var hasSelect = $(this).attr("has-select");
                var prev_el = false;
                el.on('mouseover', options.item, function (e) {
                    if (prev_el == $(this).index()) return true;
                    prev_el = $(this).index();
                    var hasClass2 = $(this).attr("has-select");

                    for (var cur_class in all_cards_classes){
                        $(this).removeClass(all_cards_classes[cur_class])
                    }

                    if (!(hasClass2 == 'true')) {
                        if ($(this).attr("has-class") == 'true') {
                            if ($(this).attr("deleted") == 'true') {
                                $(this).addClass(es_selected_has_class_del).trigger('selected');
                            } else {
                                $(this).addClass(es_selected_has_class).trigger('selected');
                            }
                        } else {
                            $(this).addClass(es_selected_no_class).trigger('selected');
                        }
                        $(this).attr("has-select", true)
                        el.trigger('selected');
                        options.onSelecting($(this));
                        options.onSelected($(this));
                        selected_items_set.add({"li": $(this), "div": el});
                        update_selected_items_text();
                    } else {
                        if ($(this).attr("has-class") == 'true') {
                            if ($(this).attr("deleted") == 'true') {
                                $(this).addClass(es_unselected_has_class_del).trigger('unselected');
                            } else {
                                $(this).addClass(es_unselected_has_class).trigger('unselected');
                            }
                        } else {
                            $(this).addClass(es_unselected_no_class).trigger('unselected');
                        }
                        $(this).attr("has-select", false)
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
                for (var cur_class in all_cards_classes){
                    $(this).removeClass(all_cards_classes[cur_class])
                }
                if (!(hasSelect == 'true')) {
                    prev_el = $(this).index();
                    if ($(this).attr("has-class") == 'true') {
                        if ($(this).attr("deleted") == 'true') {
                            $(this).addClass(es_selected_has_class_del).trigger('selected');
                        } else {
                            $(this).addClass(es_selected_has_class).trigger('selected');
                        }
                    } else {
                        $(this).addClass(es_selected_no_class).trigger('selected');
                    }
                    $(this).attr("has-select", true)
                    el.trigger('selected');
                    options.onSelecting($(this));
                    options.onSelected($(this));
                    selected_items_set.add({"li": $(this), "div": el});
                    update_selected_items_text();
                } else {
                    prev_el = $(this).index();
                    if ($(this).attr("has-class") == 'true') {
                        if ($(this).attr("deleted") == 'true') {
                            $(this).addClass(es_unselected_has_class_del).trigger('unselected');
                        } else {
                            $(this).addClass(es_unselected_has_class).trigger('unselected');
                        }
                    } else {
                        $(this).addClass(es_unselected_no_class).trigger('unselected');
                    }
                    $(this).attr("has-select", false)
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

        $('#no_class').click(function () {
            selected_items_set.forEach((item) => {
                document.getElementById('text_class_' + item["li"][0].id).innerHTML = '';

                item["li"].removeClass(es_selected_has_class).trigger('unselected');
                item["li"].removeClass(es_selected_no_class).trigger('unselected');
                item["li"].removeClass(es_selected_has_class_del).trigger('unselected');

                item["li"].attr("has-class", false);
                item["li"].attr("has-select", false);
                item["li"].attr("deleted", false);
                item["li"].addClass(es_unselected_no_class).trigger('selected');
                if (item["li"][0].id in moderated_items_set) {
                    delete moderated_items_set[item["li"][0].id]
                }
                item["div"].trigger('unselected');
                options.onSelecting(item["li"]);
                options.onUnSelected(item["li"]);
            });
            update_cards_front()
        })


        function update_cards_front() {
            let save_btn = $('#navbar_top'), save_text = $('#navbar_text');
            selected_items_set.clear();
            update_selected_items_text();
            $('#changed_items_amount').html("Changed (" + Object.keys(moderated_items_set).length + ")");
            if (save_btn != null){
                if (Object.keys(moderated_items_set).length){
                    save_text.text('Save changes');
                    save_btn.show()
                } else {
                    save_btn.hide()
                }
            }
        }

        function update_cards_data(item, el, star = null, show_original_class = true) {
            item.removeClass(es_selected_has_class).
            removeClass(es_selected_no_class).
            removeClass(es_selected_has_class_del).
            removeClass(es_unselected_has_class_del).
            trigger('unselected');
            item.attr("has-class", true);
            item.attr("has-select", false);
            if (star !== null){
                if (star){
                    item.attr("priority", "true");
                } else {
                    item.attr("priority", "false");
                }
            }
            let f = true
            let caption_id = 'text_class_' + item[0].id
            document.getElementById(caption_id).innerHTML = ''
            if (item.attr("priority") == "true"){
                document.getElementById(caption_id).innerHTML += '<span><i class="far fa-star"></i></span>'
            }

            if (el[0].getAttribute("cl_id") == "0") {
                document.getElementById(caption_id).innerHTML += item.attr('label') + '→' + '<span><i class="fas fa-trash-alt"></i></span>';
                item.attr("deleted", true);
                item.addClass(es_unselected_has_class_del).trigger('selected');
                moderated_items_set[item[0].id] = {
                    "cl": "-1",
                    "ver": item[0].getAttribute("ver"),
                    "priority": item[0].getAttribute("priority")
                }

            } else {
                if (show_original_class) {
                    document.getElementById(caption_id).innerHTML += item.attr('label') + '→';
                }
                document.getElementById(caption_id).innerHTML += el[0].getAttribute("label");
                item.attr("deleted", false);
                item.addClass(es_unselected_has_class).trigger('selected');
                moderated_items_set[item[0].id] = {
                    "cl": el[0].getAttribute("cl_id"),
                    "ver": item[0].getAttribute("ver"),
                    "priority": item[0].getAttribute("priority")
                }
            }
            item.trigger('unselected');
            options.onSelecting(item);
            options.onUnSelected(item);
        }

         $('[id^="apply_all_class_id_"]').click(function () {
             let el = $(this)
             $('li[has-select]').each(function( i ) {
                 let item = $(this)
                 update_cards_data(item, el, false);
             })
             update_cards_front()
             console.log(moderated_items_set)
        });

         $('[id^="star_apply_all_class_id_"]').click(function () {
             let el = $(this)
             $('li[has-select]').each(function( i ) {
                 let item = $(this)
                 update_cards_data(item, el, true);
             })
             update_cards_front()
             console.log(moderated_items_set)
        });

        $('[id^="class_id_"]').click(function () {
            let el = $(this)
            selected_items_set.forEach((item) => {
                update_cards_data(item["li"], el);
            });
            update_cards_front()
            console.log(moderated_items_set)
        });

        $('[id^="todo_class_id_"]').click(function () {
            let el = $(this)
            selected_items_set.forEach((item) => {
                update_cards_data(item["li"], el, null, false);
            });
            update_cards_front()
            console.log(moderated_items_set)
        });

        $('[id^="star_class_id_"]').click(function () {
            let el = $(this)
            selected_items_set.forEach((item) => {
                update_cards_data(item["li"], el, true);
            });
            update_cards_front()
            console.log(moderated_items_set)
        });

        $('[id^="no_star_class_id_"]').click(function () {
            let el = $(this)
            selected_items_set.forEach((item) => {
                update_cards_data(item["li"], el, false);
            });
            update_cards_front()
            console.log(moderated_items_set)
        });

        $('#browse_delete_imgs').click(function () {

        });


        $('#save_btn').click(function () {
            $.post("/todo/moderate/" + $('#save_btn').attr("value"), encodeURIComponent(JSON.stringify(moderated_items_set)));
            window.location.href = '/todo/index';
        });
    })

    function update_selected_items_text() {
        $('#selected_items_amount').html("Selected (" + selected_items_set.size + ")");
    }
})(jQuery);
