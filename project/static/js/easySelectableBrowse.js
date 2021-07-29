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
                var hasSelect = $(this).data("has-select");
                var prev_el = false;
                el.on('mouseover', options.item, function (e) {
                    if (prev_el == $(this).index()) return true;
                    prev_el = $(this).index();
                    var hasClass2 = $(this).data("has-select");

                    for (var cur_class in all_cards_classes){
                        console.log(all_cards_classes[cur_class])
                        $(this).removeClass(all_cards_classes[cur_class])
                    }

                    if (!hasClass2) {
                        if ($(this).data("has-class")) {
                            if ($(this).data("deleted")) {
                                $(this).addClass(es_selected_has_class_del).trigger('selected');
                            } else {
                                $(this).addClass(es_selected_has_class).trigger('selected');
                            }
                        } else {
                            $(this).addClass(es_selected_no_class).trigger('selected');
                        }
                        $(this).data("has-select", true)
                        el.trigger('selected');
                        options.onSelecting($(this));
                        options.onSelected($(this));
                        selected_items_set.add({"li": $(this), "div": el});
                        update_selected_items_text();
                    } else {
                        if ($(this).data("has-class")) {
                            if ($(this).data("deleted")) {
                                $(this).addClass(es_unselected_has_class_del).trigger('unselected');
                            } else {
                                $(this).addClass(es_unselected_has_class).trigger('unselected');
                            }
                        } else {
                            $(this).addClass(es_unselected_no_class).trigger('unselected');
                        }
                        $(this).data("has-select", false)
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
                if (!hasSelect) {
                    prev_el = $(this).index();
                    if ($(this).data("has-class")) {
                        if ($(this).data("deleted")) {
                            $(this).addClass(es_selected_has_class_del).trigger('selected');
                        } else {
                            $(this).addClass(es_selected_has_class).trigger('selected');
                        }
                    } else {
                        $(this).addClass(es_selected_no_class).trigger('selected');
                    }
                    $(this).data("has-select", true)
                    el.trigger('selected');
                    options.onSelecting($(this));
                    options.onSelected($(this));
                    selected_items_set.add({"li": $(this), "div": el});
                    update_selected_items_text();
                } else {
                    prev_el = $(this).index();
                    if ($(this).data("has-class")) {
                        if ($(this).data("deleted")) {
                            $(this).addClass(es_unselected_has_class_del).trigger('unselected');
                        } else {
                            $(this).addClass(es_unselected_has_class).trigger('unselected');
                        }
                    } else {
                        $(this).addClass(es_unselected_no_class).trigger('unselected');
                    }
                    $(this).data("has-select", false)
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
                document.getElementById('text_class_' + item["li"][0].id).innerHTML = $(this).text();

                item["li"].removeClass(es_selected_has_class).trigger('unselected');
                item["li"].removeClass(es_selected_no_class).trigger('unselected');
                item["li"].removeClass(es_selected_has_class_del).trigger('unselected');

                item["li"].data("has-class", true);
                item["li"].data("has-select", false);
                if ($(this).text() == document.getElementById('class_id_0').innerHTML) {
                    item["li"].data("deleted", true);
                    item["li"].addClass(es_unselected_has_class_del).trigger('selected');
                    moderated_items_set[item["li"][0].id] = '__del__'
                } else {
                    item["li"].data("deleted", false);
                    item["li"].addClass(es_unselected_has_class).trigger('selected');
                    moderated_items_set[item["li"][0].id] = $(this).text()
                }

                item["div"].trigger('unselected');
                options.onSelecting(item["li"]);
                options.onUnSelected(item["li"]);
            });
            selected_items_set.clear();
            update_selected_items_text();
            $('#changed_items_amount').html("Changed (" + Object.keys(moderated_items_set).length + ")");
            // $(this).prop( "checked", false );
        });

        $('#browse_delete_imgs').click(function () {

        });


        $('#save_btn').click(function () {
            console.log('ajax')
            $.post("/todo/moderate/" + $('#save_btn').attr("value"), moderated_items_set);
            window.location.href = '/todo/index';
            // $.ajax({
            //    type: "POST",
            //    contentType: "application/json; charset=utf-8",
            //    url: "/todo/moderate/"+$('#save_btn').attr("value"),
            //    data: JSON.stringify({"id": moderated_items_set}),
            //    success: [],
            //    dataType: "json"
            // }).done(function(){
            //    // $('#message').html('test');
            //     console.log('/todo/index')
            //     window.location.href = '/todo/index';
            // }).fail(function(response){
            //     console.log(response)
            //     console.log('fail?')
            //     console.log('/todo/index')
            //     // $("html").html(response)
            //     window.location.href = '/todo/index';
            //    // $('#message').html(response['responseText']);
            // });
        });
    })

    function update_selected_items_text() {
        $('#selected_items_amount').html("Selected (" + selected_items_set.size + ")");
    }
})(jQuery);
