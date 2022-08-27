var container = document.querySelectorAll('.container-table');


function button_delete(predict_id) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", `/del/${predict_id}`, false);
        xhr.send();

        // stop the engine while xhr isn't done
        for(; xhr.readyState !== 4;)

        if (xhr.status === 200) {

            console.log('SUCCESS', xhr.responseText);

        } else console.warn('request_error');
        return JSON.parse(xhr.responseText)
}



//var datetime = container.querySelector('#status');
//status = el.querySelectorAll('#st')

//console.log(container[container.length - 1].querySelector('#status'));
//console.log(container[container.length - 1].querySelector('#datetime'));

//.innerHTML = `
//${datetime.replace(/_/,'/').replace(/_/,'/').replace(/_/,'-').replace(/_/,':')}`;
function getStatus(datetime) {

    var xhr = new XMLHttpRequest();
    xhr.open("GET", `/status/${datetime}`, false);
    xhr.send();

    // stop the engine while xhr isn't done
    for(; xhr.readyState !== 4;)

    if (xhr.status === 200) {

        console.log('SUCCESS', xhr.responseText);

    } else console.warn('request_error');

    return xhr.responseText;
}

//console.log(getStatus(datetime[datetime.length - 1].textContent));

function getCategoryList(predict_id) {
//    console.log(predict_id);
    var xhr = new XMLHttpRequest();
    xhr.open("GET", `/progress/${predict_id}`, false);
    xhr.send();

    // stop the engine while xhr isn't done
//    for(; xhr.readyState !== 4;)
//
//    if (xhr.status == 200) {
//
//        console.log('SUCCESS', xhr.responseText);
//
//    } else console.warn('request_error');
    if (xhr.status != 200) {
      // обработать ошибку
      console.log( xhr.status + ': ' + xhr.statusText ); // пример вывода: 404: Not Found
    } else {
      // вывести результат
      return JSON.parse(xhr.responseText); // responseText -- текст ответа.
    }
//    return JSON.parse(xhr.responseText)
}

function progress (container) {
    let predict_id = container.querySelector("#predict_id").textContent.trim(),
     status = container.querySelector('#status'),
     result = container.querySelector('#result'),
     button = container.querySelector(".button"),
     button2 = container.querySelector(".button_del");
     button2.style.display = "flex";
//    let query = getCategoryList(predict_id);

    let elem = container.querySelector("#progress");
    let timer = setInterval(progressStatus,1000);
    function progressStatus () {
    let query = getCategoryList(predict_id);

    if (query[0].data){
//        console.log(query);
        width = query[0].data.progress;
        all_mitoz = query[0].data.mitoze;
          let progressHTML = `
            <div class="loading">
                <div class="percent"> </div>
                <div class="progress-bar">
                    <div id="progress" class="progress"></div>
                </div>
            </div>`;
        status.innerHTML = progressHTML;
        let elem = container.querySelector("#progress");
        let percent = container.querySelector('.percent')
        result.innerHTML = `<b>${all_mitoz}</b>`
      if (parseInt(width) >= 100) {
        clearInterval(timer);
        status.innerHTML = "";
        status.innerHTML = `
            Done
            <img src="/static/logo/green_check.png">
        `;
        if(button!=null){
            button.style.display = "flex"
        };
        button2.style.display = "flex";

      } else {
            query = getCategoryList(predict_id);
            width = query[0].data.progress;
            all_mitoz = query[0].data.mitoze;
            if(elem){
                elem.style.width = width + '%';
                percent.textContent = width + '%';
        }
//      else{
//        status.innerHTML = 'Process is broken';
//        clearInterval(timer);
//      }
      }
    }
  }
}

function getWork(container){
    let predict_id = container.querySelector("#predict_id").textContent.trim(),
     status = container.querySelector("#status"),
     button = container.querySelector(".button"),
     button2 = container.querySelector(".button_del");
     const fileName = container.querySelector("#name"),
    flName = fileName.textContent.split('/')[0],
    anls_num = fileName.textContent.split('/')[1]

    button2.addEventListener("click", ()=>{
        button2.innerHTML = `<img src="/static/logo/load.gif">`;
        let request = button_delete(predict_id);
        if (request == true){
            status.innerHTML = `Process killed`
            setInterval(container.replaceChildren(), 1500);
        }
        });

    if(flName.length >= 12){
                        let splitName = flName.split('.');
                        cutName = splitName[0].substring(0, 12) + "...";
                        fileName.innerHTML = `${cutName}/${anls_num}`;
                    };
    if(status.textContent.trim() == 'False'){
        status.innerHTML = `
        <img src="/static/logo/load.gif">`;
        progress(container);
    }else{
        button2.style.display = "flex";
        if(button!=null){
            button.style.display = "flex"
        }

    };
    }
for (var i = 1; i < container.length; ++i) {

    getWork(container[i]);
}
