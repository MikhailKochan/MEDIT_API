function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};
function makeProgressHTML(id, name){
    let progressHTML = `
            <li class="row" id="${id}">
                <img src="./static/logo/file.png">
                <span class="name">${name}</span>
                <div class="content">
                    <div class="details">
                        <span class="name">Uploading • </span>
                        <span class="percent"></span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="box" style="display:none;width:40%;align-items:center;justify-content:center;height: 100%">
                    <a class="button_download" href="" style="justify-content:center">Скачать</a>
                </div>
            </li>
    `;
    return progressHTML
}
var detailsElement = `
          <div class="details"style="flex-direction:row">
            <span class="func_name">Cutting • </span>
            <span class="percent"></span>
        </div>
`

$('document').ready(function(){
        $('#inputSVS').on('click', function(){
            $('.input-file').click()
        });

        $('.input-file').on('change', function(){
            $('#submit').click();
        })

        $('form').submit(function(event){
//                console.log('3');
                if($('.input-file').val())
                {
//                    console.log('4');
                    let file = $('.input-file')[0].files[0],
                    fileOriginalName = file.name,
                    name = file.name;

                    if(name.length >= 12){
                        let splitName = name.split('.');
                        name = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
                    };
                    let progressHTML = makeProgressHTML(fileOriginalName, name);

                    event.preventDefault();
                    let element_id = fileOriginalName.replaceAll('.', '\\.');

                    $(this).ajaxSubmit({
                            beforeSend: function() {
                                $('.progress-area').append(progressHTML)
                            },
                            uploadProgress: function(event, position, total, percentComplete) {

                                $(`#${element_id} > div.content > div.details > span.percent`).html(percentComplete + '%');
                                $(`#${element_id} > div.content > div.progress-bar .progress`).width(percentComplete + '%');
                                if (percentComplete >= 100) {
                                    $(`#${element_id} > div.content > div.details > span.percent`).html(`<img style="width:20px;height:20px;" src="./static/logo/load.gif">`)
                                }
                            },
                            success:function(data, status, request){
                                console.log('success');
                                $(`.progress-area > #${element_id}`).remove();
                                progressHTML = makeProgressHTML(data.task_id, name);
                                $('.uploaded-area').append(progressHTML);
                                $(`#${data.task_id} > div.content > div.details > span.percent`).html(`<img class='fa-check' src="./static/logo/green_check.png">`);
                                $(`#${data.task_id} > div.content > div.details`).after(detailsElement);

                                let status_url = request.getResponseHeader('Location');
                                update_progress(status_url, data.task_id);
                            },
                            resetForm: true,
                    });
//                    console.log('5');
                }
//                console.log('6');
            });
//        console.log('7');
        });


function update_progress(status_url, element_id) {
    // send GET request to status URL
    $.getJSON(status_url, function(data) {
        // update UI
        percent = parseInt(data['progress']);
        // #af508986-801c-4468-bafa-25a8eced0300 > div.content > div:nth-child(2) > span.percent
        $(`#${element_id} > div.content > div.progress-bar > div`).width(percent + '%');
        $(`#${element_id} > div.content > div:nth-child(2) > span.percent`).text(percent + '%');
        $(`#${element_id} > div.content > div:nth-child(2) > span.func_name`).text(`${data['function']} • `);

        if (data['state'] != 'PENDING' && data['state'] != 'PROGRESS') {
            if ('result' in data) {
                console.log(data);
                // show result #\36 f826662-1738-405a-899d-583eb07fa688 > div.box > a
                $(`#${element_id} > div.content > div:nth-child(2) > span.func_name`).text(`Cutting • `);
                $(`#${element_id} > div.content > div.progress-bar`).hide()
                $(`#${element_id} > div.content > div:nth-child(2) > span.percent`).html(`<img class='fa-check' src="./static/logo/green_check.png">`);
                $(`#${element_id} > div.box > a`).attr("href", `/get-zip/${data['filename']}.zip`)
                $(`#${element_id} > div.box`).css("display", "flex");
            }
            else {
                // something unexpected happened
                $(`#${element_id} > div.content > div:nth-child(2) > span.func_name`).text('Result: ' + data['state']);
            }
        }
        else {
            // rerun in 2 seconds
            setTimeout(function() {
                update_progress(status_url, element_id);
            }, 2000);
        }
    });
}
