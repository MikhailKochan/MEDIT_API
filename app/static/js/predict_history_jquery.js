
function delete_button_maker_logic(element_id){
    let row = $(`#${element_id}`),
    delete_button = $(`#${element_id} > div.box > .button_delete`);
    delete_button.bind('click', function() {
            $.ajax({
                url: `/del_task/${delete_button.attr('id')}`,
                type: 'DELETE',
                beforeSend: function() {
                    row.css({'z-index': 0});
                },
                success: function(result) {
                    row.css({'transform': 'translateY(-100%)'});
                    setTimeout(() => row.remove(), 1000);
                }
            });
    });
};

var container = document.querySelectorAll('.uploaded-area > .container-table');
for (var i = 0; i < container.length; ++i) {
    let element_id = container[i].id;
    delete_button_maker_logic(element_id);
};