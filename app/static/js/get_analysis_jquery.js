const form_js = document.querySelector("form");
var pause_delay = parseInt($('#pause_delay').text());

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

function makeProgressHTML(id, name){
    let progressHTML = `
        <div class="container-table" id="${id}" style="width:100%;justify-content:center">
            <div class="box" id="datetime" style="justify-content: flex-start;min-width: 192px;">
                <img src="./static/logo/file.png">
                <span class="name">${name}</span>
            </div>
            <div class="box" id="status" style="justify-content: center">
                <div class="content" style="display:flex;flex-direction:column;justify-content:center;align-items:center;min-width:0px;">
                    <div class="details" style="justify-content: center">
                        <span class="name">Загрузка</span>
                        <span class="percent"></span>
                    </div>
                    <div class="progress-bar" style="width: 90%">
                        <div class="progress" style="width: 0%"></div>
                    </div>
                </div>
            </div>
            <div class="box" id="analysis_number" style="justify-content: center;break-all;">
            </div>
            <div class="box" id="result" style="justify-content: center">
            </div>
            <div class="box">
                <a class="button_download" href="" style="display:none">
                    <img src="/static/logo/download_green.png" alt="#" title="Скачать изображения">
                </a>
                <button class="button_delete" style="display:none">
                    <img src="/static/logo/remove.png" alt="#" title="Удалить Изображения">
                </button>
            </div>
        </div>
    `;
    return progressHTML
}
var detailsElement = `
          <div class="details"style="flex-direction:row">
            <span class="func_name">Исследование</span>
            <span class="percent"></span>
        </div>
`
function cutName(name) {
    if(name.length >= 12){
        let splitName = name.split('.');
        name = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
    };
    return name
};

document.addEventListener("visibilitychange", function(){
    if(document.hidden){

    } else {
        if (startTimeTimer){
            let timeLost = Math.trunc((performance.now() - startTimeTimer) / 1000);
            clearInterval(timer);
            userTimer(window.timerTimeMinut - timeLost);
        };
    };
});

function userTimer(timeMinut){
    $('#user_timer').show();
    $('#inputSVS').hide();
    if (parseInt(timeMinut)){
        timeMinut = parseInt(timeMinut);
        var timerShow = $('#time_stamp');
        window.startTimeTimer = performance.now();
        window.timerTimeMinut = timeMinut;
        timer = setInterval(function () {
//            let start = performance.now()
            // Условие если время закончилось то...
            if (timeMinut <= 0) {
                // Таймер удаляется
                clearInterval(timer);
                $('#user_timer').hide();
                $('#inputSVS').show();
            } else { // Иначе
                document.getElementById('time_stamp').innerHTML = formatTimeLeft(timeMinut)
//                let workDelay = (performance.now() - start).toFixed(4);
//                workDelay ++;
//                console.log(workDelay);
//            console.log(timeMinut);
//            timeMinut -= workDelay;
            };

            timeMinut -= 1; // Уменьшаем таймер
//            console.log(timeMinut);
        }, 1000)
    } else {
        userTimer(100);
    };
}

function formatTimeLeft(time){
    seconds = time % 60; // Получаем секунды
    minutes = Math.trunc(time /60 % 60);// Получаем минуты
    hour = Math.trunc(time /60/60 % 60); // Получаем часы

    if (seconds < 10){
        seconds = `0${seconds}`;
    };
    if (minutes < 10){
        minutes = `0${minutes}`;
    };

    return `через ${hour}:${minutes}:${seconds}`;
}

function start(){
        $('#inputSVS').on('click', function(){
//            console.log('click');
            $('.input-file').click()
        });

        $('.input-file').on('change', function(){
            $('#submit').click();
        })

        $('form').submit(function(event){

                if($('.input-file').val())
                {
                    let file = $('.input-file')[0].files[0],
                    fileType = getExtension(file.name);
                    let validExtensions = ["svs", "zip"];
                    if(validExtensions.includes(fileType)){
                        let fileOriginalName = file.name,
                        name = file.name;
                        $('#inputSVS').hide();

                        name = cutName(name);
                        let element_id = fileOriginalName.replaceAll('.', '\\.');
                        let progressHTML = makeProgressHTML(fileOriginalName, name);

                        event.preventDefault();

                        $(this).ajaxSubmit({
                                beforeSend: function() {
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
                                    $('#inputSVS').show();
                                    userTimer(pause_delay);
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
                    }else{
                        alert('Такой формат файла пока не поддерживается');
                        $('form').reset();
                    }
                };
    })
}

$('document').ready(function(){
        var user_access = $('#user_access').text();
        $('#user_timer').hide();
        $('#inputSVS').hide();
        start();
        if(parseInt(user_access)){
                userTimer(parseInt(user_access));
            } else if (parseInt(user_access) == 0) {
                $('#inputSVS').show();
            } else{
                userTimer(20);
            };
        });

function update_progress(status_url, element_id) {
    // send GET request to status URL
    $.getJSON(status_url, function(data) {
        // update UI
//        console.log(data);
        percent = parseInt(data['progress']);
        if (percent) {
            $(`#${element_id} > #status > div > div.progress-bar > div`).width(data['progress'] + '%');
            $(`#${element_id} > #status > div > div.details > span.percent`).text(percent + '%');
        };
        let infoFunc = data['function'];
        if (infoFunc == 'Predict'){
            infoFunc = 'Исследование';
        }else if (infoFunc == 'Create zip'){
                infoFunc = 'Архивация данных';
            } else if(infoFunc == 'unzip'){
                infoFunc = 'Подготовка данных';
            };
        if (data['state'] == 'PENDING') {
            infoFunc = 'В очереди'
        };
        if (infoFunc){
            $(`#${element_id} > #status > div > div.details > span.name`).text(`${infoFunc}`);
        };
        if ('all_mitoses' in data && data['all_mitoses']){
//            console.log(data['all_mitoz'])
            $(`#${element_id} > #result`).text(`${data['all_mitoses']}`)
        }
        if ('analysis_number' in data && data['analysis_number']){
            $(`#${element_id} > #analysis_number`).text(`${data['analysis_number']}`);
        }
        if (data['state'] != 'PENDING' && data['state'] != 'PROGRESS') {
//            console.log(data);
//            if ('result' in data) {
//                console.log(data);
                if (data['state'] == 'SUCCESS') {
                            $(`#${element_id} > #status > div > div.details`).css('margin-top', 0);
                            if (data['filename']) {
                               $(`#${element_id} > div.box > a.button_download`).attr("href", `/get-zip/${data['zipname']}`);
                            };
                            delete_button_maker_logic(element_id);
                            $(`#${element_id} > #status > div > div.details > span.name`).text('Исследование завершено');
                            $(`#${element_id}>#status > div > div.details > span.percent`).html(`<img class='fa-check' src="./static/logo/green_check.png">`);
                        };
                $(`#${element_id} > #status > div > div.progress-bar`).hide();

                $(`#${element_id} > div:nth-child(5) > a`).css("display", "flex");
                $(`#${element_id} > div.box > .button_delete`).css("display", "flex");
//            } else {
//                // something unexpected happened
////                console.log(data);
//                $(`#${element_id} > div.content > div:nth-child(2) > span.func_name`).text('Result: ' + data['state']);
//            }
        }
        else {
            // rerun in 2 seconds
//            console.log('4');
            setTimeout(function() {
                update_progress(status_url, element_id);
            }, 5000);
        }
    });
}

function delete_button_maker_logic(element_id){
    let row = $(`#${element_id}`),
    delete_button = $(`#${element_id} > div.box > .button_delete`);
    delete_button.bind('click', function() {
            $.ajax({
                url: `/del_task/${element_id}`,
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
    let status_url = `/progress/${element_id}`;
    let name = $(`#${element_id} > #datetime > span`).text()
    name = cutName(name);
    $(`#${element_id} > #datetime > span`).html(name);
//    delete_button_maker_logic(element_id);
    update_progress(status_url, element_id);
}