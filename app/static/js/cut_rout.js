const form = document.querySelector("form"),
bottomFile = document.querySelector("button"),
bottomCutFile = document.querySelector(".button_download"),
fileInput = form.querySelector(".input-file"),
dateTime = document.querySelector("#datetime"),
progressArea = document.querySelector(".progress-area"),
uploadedArea = document.querySelector(".uploaded-area");
let status = document.querySelector("#status");


function getCategoryList(img_id) {
    var data = new FormData();
    data.append('Image_id', img_id);
    var xhr = new XMLHttpRequest();
    xhr.open("POST", `/progress/post`, false);
    xhr.send(data);

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

function progress (predict_id) {

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

//    var myTimeout = setTimeout(function run(){
//        let req = getCategoryList(fileOriginalName);
//            if (Object.keys(req[0].data.func) == 'cutting') {
//
//                setTimeout(run, 1000);
//            }else{
//                progressStatus(fileOriginalName);
//            };
//        }, 1000);

    let timer = setInterval(progressStatus,2000);

    function progressStatus () {

    let query = getCategoryList(predict_id);

    if (query[0].data){
        if (query[0].data.in_queries == 'Please_wait'){
            status.innerHTML = "Ваша задача в очереди";
        } else{
         if (Object.keys(query[0].data.func) == 'cutting'){

            width = query[0].data.func.cutting.progress;
        }else{
            status.innerHTML = "";
            status.innerHTML = `
                    Done
                    <img src="/static/logo/green_check.png">
                `;
            result.innerHTML = progressHTML;

            width = query[0].data.func.create_zip.progress;
            if (parseInt(width) >= 100) {
                clearInterval(timer);
                result.innerHTML = "";
                result.innerHTML = `
                    Done
                    <img src="/static/logo/green_check.png">
                `;
                bottomCutFile.href = `/get-zip/${predict_id}.zip`
                bottomCutFile.style.display = 'flex';
                }
        }

        let elem = document.querySelector("#progress");
        let percent = document.querySelector('.percent')

      if (parseInt(width) >= 100) {
        clearInterval(timer);

        status.innerHTML = "";
        status.innerHTML = `
            Done
            <img src="/static/logo/green_check.png">
        `;
        result.innerHTML = progressHTML;
        let timer = setInterval(progressStatus,2000);
      } else {

            if(elem){
                elem.style.width = width + '%';
                percent.textContent = width + '%';
        }

      }
    }
  }
}};

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

console.log(fileInput.onchange);

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
                let fileOriginalName = file.name;
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
                    setTimeout(run, 1000);
                }else{
                    progress(fileOriginalName);
                };
           }, 5000);

       }
    });
    let formData = new FormData(form);
    xhr.send(formData);
}