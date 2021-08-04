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
                        console.log(all_cards_classes[cur_class])
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
                    console.log(all_cards_classes[cur_class])
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
            let save_btn = $('#navbar_top')
            let save_text = $('#navbar_text')
            selected_items_set.forEach((item) => {
                document.getElementById('text_class_' + item["li"][0].id).innerHTML = '';

                item["li"].removeClass(es_selected_has_class).trigger('unselected');
                item["li"].removeClass(es_selected_no_class).trigger('unselected');
                item["li"].removeClass(es_selected_has_class_del).trigger('unselected');

                item["li"].attr("has-class", false);
                item["li"].attr("has-select", false);
                item["li"].attr("deleted", false);
                item["li"].addClass(es_unselected_has_class).trigger('selected');
                if (item["li"][0].id in moderated_items_set) {
                    delete moderated_items_set[item["li"][0].id]
                }
                item["div"].trigger('unselected');
                options.onSelecting(item["li"]);
                options.onUnSelected(item["li"]);
            });
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
        })

        $('[id^="class_id_"]').click(function () {
            let save_btn = $('#navbar_top')
            let save_text = $('#navbar_text')
            let del_btn = document.getElementById('class_id_0')
            // let no_class_btn = document.getElementById('class_id_no_class')

            selected_items_set.forEach((item) => {
                document.getElementById('text_class_' + item["li"][0].id).innerHTML = $(this).text();

                item["li"].removeClass(es_selected_has_class).trigger('unselected');
                item["li"].removeClass(es_selected_no_class).trigger('unselected');
                item["li"].removeClass(es_selected_has_class_del).trigger('unselected');

                item["li"].attr("has-class", true);
                item["li"].attr("has-select", false);
                let f = true
                if (del_btn != null){
                    if ($(this).text() == del_btn.innerHTML) {
                        item["li"].attr("deleted", true);
                        item["li"].addClass(es_unselected_has_class_del).trigger('selected');
                        moderated_items_set[item["li"][0].id] = {"cl": "-1", "ver": item["li"][0].getAttribute("ver")}
                        f = false
                    }
                }
                if (f) {
                        item["li"].attr("deleted", false);
                        item["li"].addClass(es_unselected_has_class).trigger('selected');
                        moderated_items_set[item["li"][0].id] = {"cl": $(this)[0].getAttribute("cl_id"), "ver": item["li"][0].getAttribute("ver")}
                }


                item["div"].trigger('unselected');
                options.onSelecting(item["li"]);
                options.onUnSelected(item["li"]);
            });
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
        });

        $('#browse_delete_imgs').click(function () {

        });


        $('#save_btn').click(function () {
            console.log('ajax')
            $.post("/todo/moderate/" + $('#save_btn').attr("value"), encodeURIComponent(JSON.stringify(moderated_items_set)));
            window.location.href = '/todo/index';
        });
    })

    function update_selected_items_text() {
        $('#selected_items_amount').html("Unsaved (" + selected_items_set.size + ")");
    }
})(jQuery);
