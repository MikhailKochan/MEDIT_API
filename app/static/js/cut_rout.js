const form = document.querySelector("form"),
bottomFile = document.querySelector("button"),
bottomCutFile = document.querySelector(".button_download"),
fileInput = form.querySelector(".input-file"),
dateTime = document.querySelector("#datetime"),
progressArea = document.querySelector(".progress-area"),
uploadedArea = document.querySelector(".uploaded-area");
let status = document.querySelector("#status"),
result = document.querySelector("#result");


function getProgress(task_id) {
//    var data = new FormData();
//    data.append('Image_id', img_id);
    var xhr = new XMLHttpRequest();
    xhr.open("get", `/progress/${task_id}`, false);
    xhr.send();

    if (xhr.status != 200) {
      // обработать ошибку
//      console.log( xhr.status + ': ' + xhr.statusText ); // пример вывода: 404: Not Found
        return false
    } else {
      // вывести результат
//      clearInterval(myTimeout);
//      console.log(JSON.parse(xhr.responseText));
      return JSON.parse(xhr.responseText) // responseText -- текст ответа.
    }
}

function redisDel(key) {
//    var data = new FormData();
//    data.append('Image_id', img_id);
    var xhr = new XMLHttpRequest();
    xhr.open("get", `/redis-delete/${key}`, false);
    xhr.send();

    if (xhr.status != 200) {
      // обработать ошибку
//      console.log( xhr.status + ': ' + xhr.statusText ); // пример вывода: 404: Not Found
        return false
    } else {
      // вывести результат
//      clearInterval(myTimeout);
//      console.log(JSON.parse(xhr.responseText));
      return JSON.parse(xhr.responseText) // responseText -- текст ответа.
    }
}

function getCategoryList(img_name) {
//    var data = new FormData();
//    data.append('Image_id', img_id);
    var xhr = new XMLHttpRequest();
    xhr.open("get", `/get/${img_name}`, false);
    xhr.send();

    if (xhr.status != 200) {
      // обработать ошибку
//      console.log( xhr.status + ': ' + xhr.statusText ); // пример вывода: 404: Not Found
        return false
    } else {
      // вывести результат
//      clearInterval(myTimeout);
//      console.log(JSON.parse(xhr.responseText));
      return JSON.parse(xhr.responseText) // responseText -- текст ответа.
    }
}

function progress (task_id) {

    let status = document.querySelector("#status"),
    result = document.querySelector("#result");

    let progressHTML = `
        <div class="loading">
            <div class="percent"> </div>
            <div class="progress-bar">
                <div id="progress" class="progress"></div>
            </div>
        </div>`;

    status.innerHTML = progressHTML;

    let timer = setTimeout(progressStatus, 1000);

    function progressStatus () {

    let query = getProgress(task_id);

//    console.log(query);

    if (query != false){
        if (query.data.in_queries == 'Please_wait'){

            status.innerHTML = "Ваша задача в очереди";
            let timer = setTimeout(progressStatus, 1000);

        } else {
             if (Object.keys(query.data.func) == 'cutting'){
//                console.log(query);
                width = query.data.func.cutting.progress;

            } else {
//                console.log(query);
                status.innerHTML = "";
                status.innerHTML = `
                        Done
                        <img src="/static/logo/green_check.png">
                    `;
                result.innerHTML = progressHTML;

                width = query.data.func.create_zip.progress;
                console.log(width);

                if (parseInt(width) >= 100) {

                    result.innerHTML = "";
                    result.innerHTML = `
                        Done
                        <img src="/static/logo/green_check.png">
                    `;
                    bottomCutFile.href = `/get-zip/${query.data.filename}.zip`
                    bottomCutFile.style.display = 'flex';

                    redisDel(task_id);
                    return
                    }


            };

        let elem = document.querySelector("#progress");
        let percent = document.querySelector('.percent');

      if (parseInt(width) >= 100) {

        status.innerHTML = "";
        status.innerHTML = `
            Done
            <img src="/static/logo/green_check.png">
        `;
        result.innerHTML = progressHTML;
        let timer = setTimeout(progressStatus, 1000);
      } else {
            if(elem){
                elem.style.width = width + '%';
                percent.textContent = width + '%';
        }
        let timer = setTimeout(progressStatus, 500);
      }
    }
  }else{
//    clearInterval(timer);
    let timer = setTimeout(progressStatus, 1000);
  }
}};

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

bottomCutFile.addEventListener("click", ()=>{
    bottomCutFile.click();
    setTimeout(clearForm, 1000);
    function clearForm () {
        document.querySelector("#name").innerHTML = "";
        dateTime.innerHTML = `
            <form action="{{url_for('main.cut_rout')}}" style="margin-top:0%" enctype="multiple / form-data">
            <input type="file" name="file" class="input-file" hidden>
            <button class="button" type="button" style="margin-top:0%">Выбрать файл</button></form>
        `;
        progressArea.innerHTML = "";
        form.reset();
        status.innerHTML = "";
        result.innerHTML = "";
        bottomCutFile.style.display = 'none';
        setTimeout(delZip, 5000)
        function delZip () {
            let bottomCutFile = document.querySelector(".button_download");
            let key = bottomCutFile.href.split('/');
            console.log(bottomCutFile.href);
            console.log(bottomCutFile.href.split('/'));
//            var xhr = new XMLHttpRequest();
//            xhr.open("get", `/zip-delete/${key}`, false);
//            xhr.send();
        }
    }
});

bottomFile.addEventListener("click", ()=>{
    fileInput.click();
});


form.onchange = ({target}) =>{

        let file = target.files[0];
        let fileName = file.name;
        if(fileName.length >= 12){
                    let splitName = fileName.split('.');
                    fileName = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
                }

        let afterCheckFileHTML = `
            <img src="/static/logo/file.png" style="border-radius:0;">
            <span class="name">${fileName}</span>
        `;


        let  fileType = getExtension(file.name);
        let validExtensions = ["svs"];
        if(validExtensions.includes(fileType)){
            if(file){
                dateTime.innerHTML = afterCheckFileHTML;
                let fileName = file.name;
                var fileOriginalName = file.name;
                if(fileName.length >= 12){
                    let splitName = fileName.split('.');
                    fileName = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
                }
                uploadFile(fileName, fileOriginalName);
            }
        }else{
            alert('Такой формат файла пока не поддерживается');
            form.reset()
        }
    };

function uploadFile(name, fileOriginalName){
    let xhr = new XMLHttpRequest();
    xhr.open("POST", '/cutting');
    xhr.upload.addEventListener("progress", ({loaded, total}) =>{
       let fileLoaded = Math.floor((loaded / total) * 100);
       let fileTotal = Math.floor(total / 1000)
       let fileSize;
       (fileTotal < 1024) ? fileSize = fileTotal + "KB" : fileSize = (loaded / (1024 * 1024)).toFixed(2) + "MB";
       let progressHTML = `
                <li class="box" style="border:none;justify-content:center">
                    <div class="content" style="justify-content: center">
                        <div class="details" style="justify-content: center">
                            <span class="percent">${fileLoaded}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress" style="width: ${fileLoaded}%"></div>
                        </div>
                </li>
        `;
       progressArea.innerHTML = progressHTML;
       if(loaded == total){
           progressArea.innerHTML = "";
           let uploadedHTML = `
                    <img src="/static/logo/green_check.png">
                `;
           uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);
            let loadGif = `
                <img src="/static/logo/load.gif">
            `
            status.insertAdjacentHTML("afterbegin", loadGif)
           var myTimeout = setTimeout(function run(){
                let req = getCategoryList(fileOriginalName);
                if (req === false) {
                    console.log('req is false, start func run again');
                    setTimeout(run, 1000);
                }else{
                    clearTimeout(myTimeout);
                    console.log(req);
                    progress(req.task_id);
                };
           }, 5000);

       }
    });
    let formData = new FormData(form);
    xhr.send(formData);
}