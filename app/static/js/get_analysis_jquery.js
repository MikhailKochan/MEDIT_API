

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

function makeProgressHTML(id, name){
    let progressHTML = `
        <div class="container-table" id="${id}" style="width:100%;justify-content:center">
            <div class="box" id="datetime" style="justify-content: flex-start;">
                <img src="./static/logo/file.png">
                <span class="name">${name}</span>
            </div>
            <div class="box" id="status" style="justify-content: center">
                <div class="content" style="justify-content: center; align-items: center">
                    <div class="details" style="justify-content: center">
                        <span class="name">Загрузка • </span>
                        <span class="percent"></span>
                    </div>
                    <div class="progress-bar" style="width: 90%">
                        <div class="progress" style="width: 0%"></div>
                    </div>
                </div>
            </div>
            <div class="box" id="analysis_number" style="justify-content: center">
            </div>
            <div class="box" id="result" style="justify-content: center">
            </div>
            <div class="box">
                <a class="button_download" href="" style="display:none"><img src="/static/logo/download.png" alt="#">Скачать</a><br>
            </div>
        </div>
    `;
    return progressHTML
}
var detailsElement = `
          <div class="details"style="flex-direction:row">
            <span class="func_name">Анализ • </span>
            <span class="percent"></span>
        </div>
`
function cutName(name) {
    if(name.length >= 12){
        let splitName = name.split('.');
        name = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
    };
    return name
}
$('document').ready(function(){
        $('#inputSVS').on('click', function(){
            console.log('click');
            $('.input-file').click()
        });

        $('.input-file').on('change', function(){
            $('#submit').click();
        })

        $('form').submit(function(event){

                if($('.input-file').val())
                {

                    let file = $('.input-file')[0].files[0],
                    fileOriginalName = file.name,
                    name = file.name;

//                    if(name.length >= 8){
//                        let splitName = name.split('.');
//                        name = splitName[0].substring(0, 8) + "... ." + splitName[splitName.length - 1];
//                    };
                    name = cutName(name);
                    let element_id = fileOriginalName.replaceAll('.', '\\.');
                    let progressHTML = makeProgressHTML(fileOriginalName, name);

                    event.preventDefault();


                    $(this).ajaxSubmit({
                            beforeSend: function() {
//                                console.log(progressHTML);
                                $('.progress-area').append(progressHTML)
                            },

                            uploadProgress: function(event, position, total, percentComplete) {
//                                console.log(percentComplete + '%');
                                $(`#${element_id}>#status > div > div.details > span.percent`).html(percentComplete + '%');
                                $(`#${element_id}>#status > div > div.progress-bar > div`).width(percentComplete + '%');

                                if (percentComplete >= 100) {
                                    $(`#${element_id}>#status > div > div.details > span.percent`).html(`<img style="width:20px;height:20px;" src="./static/logo/load.gif">`)
                                }
                            },
                            success:function(data, status, request){
//                                console.log('success');
                                $(`.progress-area > #${element_id}`).remove();
                                progressHTML = makeProgressHTML(data.task_id, name);
//                                console.log(progressHTML);
                                $('.uploaded-area').append(progressHTML);

                                $(`#${data.task_id} > div.content > div.details`).after(detailsElement);

                                let status_url = request.getResponseHeader('Location');
                                update_progress(status_url, data.task_id);
                            },
                            resetForm: true,
                    });

                }

            });

        });

function update_progress(status_url, element_id) {
    // send GET request to status URL
    $.getJSON(status_url, function(data) {
        // update UI
//        console.log(data['state']);
        percent = parseInt(data['progress']);
        if (percent) {
            $(`#${element_id} > #status > div > div.progress-bar > div`).width(percent + '%');
            $(`#${element_id} > #status > div > div.details > span.percent`).text(percent + '%');
        };
        let infoFunc = data['function'];
        if (infoFunc == 'Predict'){
            infoFunc = 'Исследование';
        }else if (infoFunc == 'Create zip'){
                infoFunc = 'Архивация данных';
            }
        if (data['state'] == 'PENDING') {
            infoFunc = 'В очереди'
        };
        $(`#${element_id} > #status > div > div.details > span.name`).text(`${infoFunc}`);

        if ('all_mitoz' in data){
//            console.log(data['all_mitoz'])
            $(`#${element_id} > #result`).text(`${data['all_mitoz']}`)
        }
        if ('analysis_number' in data){
            $(`#${element_id} > #analysis_number`).text(`${data['analysis_number']}`);
        }
        if (data['state'] != 'PENDING' && data['state'] != 'PROGRESS') {
//            console.log('1');
            if ('result' in data) {
//                console.log('2');
                $(`#${element_id} > #status > div > div.details > span.name`).text(`${data['state']}`);
                $(`#${element_id} > #status > div > div.progress-bar`).hide()
                $(`#${element_id}>#status > div > div.details > span.percent`).html(`<img class='fa-check' src="./static/logo/green_check.png">`);
                $(`#${element_id} > div.box > a.button_download`).attr("href", `/get-zip/${data['filename']}.zip`)
                $(`#${element_id} > div:nth-child(5) > a`).css("display", "flex");
            }
            else {
                // something unexpected happened
//                console.log('3');
                $(`#${element_id} > div.content > div:nth-child(2) > span.func_name`).text('Result: ' + data['state']);
            }
        }
        else {
            // rerun in 2 seconds
//            console.log('4');
            setTimeout(function() {
                update_progress(status_url, element_id);
            }, 2000);
        }
    });
}

var container = document.querySelectorAll('.uploaded-area > .container-table');

for (var i = 0; i < container.length; ++i) {
    let element_id = container[i].id;
    let status_url = `/progress/${container[i].id}`;
    let name = $(`#${element_id} > #datetime > span`).text()
    name = cutName(name);
    $(`#${element_id} > #datetime > span`).html(name)
    update_progress(status_url, element_id);
}