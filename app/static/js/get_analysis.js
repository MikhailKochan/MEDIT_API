const form = document.querySelector("form"),
bottomInputFile = document.querySelector("button"),
bottomDownloadFile = document.querySelector(".button_download"),
fileInput = form.querySelector(".input-file"),
span_name = document.querySelector(".span_name"),
dateTime = document.querySelector("#datetime"),
imgPNG_file = document.querySelector("#img_file"),
progressArea = document.querySelector(".progress-area"),
uploadedArea = document.querySelector(".uploaded-area");

function getProgress(url, key) {
//    var data = new FormData();
//    data.append('Image_id', img_id);
    var xhr = new XMLHttpRequest();
    xhr.open("get", `/${url}/${key}`, false);
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

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

bottomInputFile.addEventListener("click", ()=>{
    fileInput.click();
});

form.onchange = ({target}) =>{
        let file = target.files[0];
        let  fileType = getExtension(file.name);
        let validExtensions = ["svs"];
        if(validExtensions.includes(fileType)){
            if(file){
                let fileName = file.name;
                var fileOriginalName = file.name;
                if(fileName.length >= 12){
                    let splitName = fileName.split('.');
                    fileName = splitName[0].substring(0, 12) + "... ." + splitName[splitName.length - 1];
                };
                bottomInputFile.style.display = 'none';
//                dateTime.insertAdjacentHTML('beforeend', afterCheckFileHTML);

                uploadFile(fileName, fileOriginalName);
            }
        }else{
            alert('Такой формат файла пока не поддерживается');
            form.reset()
        }
    };

function uploadFile(name, fileOriginalName){
    let xhr = new XMLHttpRequest();
    xhr.open("POST", '/upload');
    xhr.upload.addEventListener("progress", ({loaded, total}) =>{
       let fileLoaded = Math.floor((loaded / total) * 100);
       let fileTotal = Math.floor(total / 1000)
       let fileSize;
       (fileTotal < 1024) ? fileSize = fileTotal + "KB" : fileSize = (loaded / (1024 * 1024)).toFixed(2) + "MB";
       let progressHTML = `
                <li class="row" style="margin:0%;margin-bottom:0px;padding:0px">
                    <img src="./static/logo/file.png">
                    <div class="content" style='background:none;'>
                        <div class="details">
                            <span class="name">${name}</span>
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
//           progressArea.innerHTML = `Загрузка <img src='/static/logo/check.png'>`;
           let uploadedHTML = `
                <li class="row" style="margin:0%;margin-bottom:0px;padding:0px">
                    <div class="content" style='background:none;'>
                        <img src="/static/logo/file.png" style="margin-right:10px;margin-left:0px;">
                         <div class="details">
                            <span class="name">${name}</span>
                            <span class="size">${fileSize}</span>
                        </div>
                    </div>

                `;
                uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);
                imgPNG_file.style.display = 'flex';
           var myTimeout = setTimeout(function run(){
                let req = getProgress('get', fileOriginalName);
                if (req === false) {
                    console.log('req is false, start func run again');
                    setTimeout(run, 1000);
                }else{
                    clearTimeout(myTimeout);
                    console.log(req);
//                    progress(req.task_id);
                };
           }, 5000);

       }
    });
    let formData = new FormData(form);
    xhr.send(formData);
}