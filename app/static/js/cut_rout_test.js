const form = document.querySelector("form"),
fileInput = form.querySelector(".input-file"),
bottomInputFile = document.querySelector("button"),
progressArea = document.querySelector(".progress-area"),
data_enable = document.querySelectorAll(".data_enable"),
uploadedArea = document.querySelector(".uploaded-area");

//console.log(data_enable);

bottomInputFile.addEventListener("click", ()=>{
//    bottomInputFile.style.boxShadow = 'rgba(50, 50, 93, 0.25) 0px 10px 30px -12px inset, rgba(0, 0, 0, 0.3) 0px 8px 10px -10px inset';
    fileInput.click();
});

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

function getProgress(url, key) {
    var xhr = new XMLHttpRequest();
    xhr.open("get", `/${url}/${key}`, false);
    xhr.send();

    if (xhr.status != 200) {

        return false
    } else {
      // вывести результат
//      clearInterval(myTimeout);
//      console.log(JSON.parse(xhr.responseText));
      return JSON.parse(xhr.responseText) // responseText -- текст ответа.
    }
};


fileInput.onchange = ({target}) =>{
//    for (var i = 0; i < target.files.length; ++i) {
        let file = target.files[0];
        if(file){
            let  fileType = getExtension(file.name);
    //        console.log(file);
            let validExtensions = ["svs"];
            if(validExtensions.includes(fileType)){
                let fileName = file.name;
                let fileOriginalName = file.name;
                if(fileName.length >= 12){
                    let splitName = fileName.split('.');
                    fileName = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
                }
                uploadFile(fileName, fileOriginalName);
            }else{
                alert('Такой формат файла пока не поддерживается');
        }
        }
    };
//    console.log("after FOR");

//}

function uploadFile(name, fileOriginalName){
    let xhr = new XMLHttpRequest();
    xhr.open("POST", '/cutting');
    xhr.upload.addEventListener("progress", ({loaded, total}) =>{
       let fileLoaded = Math.floor((loaded / total) * 100);
       let fileTotal = Math.floor(total / 1000)
       let fileSize;
       (fileTotal < 1024) ? fileSize = fileTotal + "KB" : fileSize = (loaded / (1024 * 1024)).toFixed(2) + "MB";
       let progressHTML = `
                <li class="row">
                    <img src="./static/logo/file.png">
                    <div class="content">
                        <div class="details">
                            <span class="name">${name} • Uploading</span>
                            <span class="percent">${fileLoaded}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress" style="width: ${fileLoaded}%"></div>
                        </div>
                </li>
        `;
       progressArea.innerHTML = progressHTML;
       bottomInputFile.style.pointerEvents = 'none';
       bottomInputFile.style.background = '#888';
       if(loaded == total){
           progressArea.innerHTML = "";

           let uploadedHTML = `
                <li class="row" id="${fileOriginalName}">
                    <img src="./static/logo/file.png">
                    <span>${name}</span>
                    <div class="content" style="justify-content:space-around">
                         <div class="details" >
                            <span class="name" style="display:flex;align-items:center;width:100%;">Uploading • <img class='fa-check' src="./static/logo/green_check.png"></span>
                            <span class="size">${fileSize}</span>
                        </div>
                        <div class="details"style="flex-direction:row">
                            <span class="func_name">Cutting • </span>
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
                uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);

                bottomInputFile.style.pointerEvents = 'auto';
                bottomInputFile.style.background = '#eff1f4';

                var myTimeout = setTimeout(function run(){
                    let workArea = document.querySelector("#" + `${fileOriginalName.replaceAll('.', '\\.')}`);
                    let req = getProgress('get', fileOriginalName);
                    if (req === false) {
                        console.log('req is false, start func run again');
                        setTimeout(run, 1000);
                    }else{
                        clearTimeout(myTimeout);;
                        progress(req.task_id, workArea);
                    };
                }, 5000);
       }
    });
    let formData = new FormData(form);
    xhr.send(formData);
};

function progress (task_id, workArea) {

    let timer = setTimeout(function() {
        progressStatus(workArea);
    }, 2000);

    function progressStatus (workArea) {

        let query = getProgress('progress', task_id);

        let span_func_name = workArea.children[2].children[1].children[0];
        let elem = workArea.children[2].children[2].children[0];
        let percent = workArea.children[2].children[1].children[1];
        let bottomDownloadFile = workArea.children[3];

        if (query != false){
            if (query.data.in_queries == 'Please_wait'){

                percent.innerHTML = "В очереди";
                let timer = setTimeout(function() {
                        progressStatus(workArea);
                    }, 10000);

            } else {

                span_func_name.innerHTML = `${query.data.func} • `;
                let width = query.data.progress;

              if (parseInt(width) >= 100) {

                if (query.data.func == "Create_zip"){
//                    console.log('we in == Create_zip');
                    workArea.children[2].children[2].style.display = 'none';
                    span_func_name.innerHTML = `Cutting • `
                    percent.innerHTML = `<img class='fa-check' src="/static/logo/green_check.png">`;
                    bottomDownloadFile.children[0].href = `/get-zip/${query.data.filename}.zip`;
                    bottomDownloadFile.style.display = 'flex';
                    getProgress('redis-delete', task_id);
                    return
                }else{
                    let timer = setTimeout(function() {
                        progressStatus(workArea);
                    }, 2000);
                };
              } else {
//                    console.log('we in width != 100');
                    if(elem){
                        elem.style.width = width + '%';
                        percent.textContent = width + '%';
                    };
                    let timer = setTimeout(function() {
                        progressStatus(workArea);
                    }, 2000);
              }
            };
        }else{
            let timer = setTimeout(function() {
                progressStatus(workArea);
            }, 2000);
        }
    }
};

if (data_enable) {
    for (var i = 0; i < data_enable.length; ++i) {
        let fileOriginalName = data_enable[i].textContent.trim().split('\n')[1].replace(/\s+/g,''),
        task_id = data_enable[i].textContent.trim().split('\n')[0].replace(/\s+/g,''),
        name = fileOriginalName;
//        console.log(fileOriginalName);
        if(fileOriginalName.length >= 12){
                    let splitName = fileOriginalName.split('.');
                    name = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
                };

        let uploadedHTML = `
                <li class="row" id="${fileOriginalName}">
                    <img src="./static/logo/file.png">
                    <span>${name}</span>
                    <div class="content" style="justify-content:space-around">
                         <div class="details" >
                            <span class="name" style="display:flex;align-items:center;width:100%;">Uploading • <img class='fa-check' src="./static/logo/green_check.png"></span>

                        </div>
                        <div class="details"style="flex-direction:row">
                            <span class="func_name">Cutting • </span>
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
        uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);
        let id_element = fileOriginalName.replaceAll('.', '\\.');
//        console.log(id_element);
        let workArea = document.querySelector("#" + `${id_element}`);
//        console.log(workArea);
        progress(task_id, workArea);
    };
}