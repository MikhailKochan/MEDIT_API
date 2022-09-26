const form = document.querySelector("form"),
fileInput = form.querySelector(".input-file"),
bottomInputFile = document.querySelector("button"),
progressArea = document.querySelector(".progress-area"),
uploadedArea = document.querySelector(".uploaded-area");


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
                    <div class="content" style="justify-content:space-around">
                         <div class="details">
                            <span class="name">${name} • Uploading <img class='fa-check' src="./static/logo/green_check.png"></span>
                            <span class="size">${fileSize}</span>
                        </div>
                        <div class="details"style="flex-direction:row">
                            <span class="func_name">Cutting • </span>
                            <span class="percent">0%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress" style="width: 0%"></div>
                        </div>
                </li>
                `;
                uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);
                let workArea = document.querySelector("#" + `${fileOriginalName.replaceAll('.', '\\.')}`);
                console.log(workArea);
                bottomInputFile.style.pointerEvents = 'auto';
                bottomInputFile.style.background = '#eff1f4'
                var myTimeout = setTimeout(function run(){
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

    let timer = setTimeout(progressStatus, 1000);

    function progressStatus (workArea) {

        let query = getProgress('progress', task_id);

        let elem = workArea.querySelector(".progress");
        let percent = workArea.querySelector('.percent');

        if (query != false){
            if (query.data.in_queries == 'Please_wait'){

                percent.innerHTML = "В очереди";
                let timer = setTimeout(progressStatus, 5000);

            } else {

//                span_name.innerHTML = `${query.data.func} • `;
                let width = query.data.progress;

              if (parseInt(width) >= 100) {

//                progressArea.innerHTML = "";
//                progressArea.innerHTML = `
//                    <span style="margin:5%;">Done</span>
//                    <img src="/static/logo/green_check.png">
//                `;
                if (query.data.func == "create_zip"){
                    console.log('we in == create_zip');
                    bottomDownloadFile.href = `/get-zip/${query.data.filename}.zip`
                    bottomDownloadFile.style.display = 'flex';
                    getProgress('redis-delete', task_id);
                    return
                }else{
                    let timer = setTimeout(progressStatus, 500);
                };
              } else {
//                    console.log('we in width != 100');
                    if(elem){
                        elem.style.width = width + '%';
                        percent.textContent = width + '%';
                    };
                    let timer = setTimeout(progressStatus, 500);
              }
            };
        }else{
            let timer = setTimeout(progressStatus, 1000);
        }
    }
};