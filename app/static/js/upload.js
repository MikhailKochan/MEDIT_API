const form = document.querySelector("form"),
fileInput = form.querySelector(".input-file"),
progressArea = document.querySelector(".progress-area"),
uploadedArea = document.querySelector(".uploaded-area");



form.addEventListener("click", ()=>{
    fileInput.click();
});

function getExtension(filename) {
  var parts = filename.split('.');
  return parts[parts.length - 1];
};

function myGreeting(name){

   const xhr = new XMLHttpRequest();
    xhr.open("GET", `/get/${name}`, false);
    xhr.onreadystatechange = handleFunc;
    xhr.send();
    function handleFunc(){
        if(xhr.status != 200){
            console.log("don't have response...");
            return false
        }else{
            let url = JSON.parse(xhr.responseText);
            console.log(url);
            if(url != ""){
            window.location.replace(`/new_analysis/${url}`)
        }
    }

}}

fileInput.onchange = ({target}) =>{

//    for (var i = 0; i < target.files.length; ++i) {
        let file = target.files[0];
        let  fileType = getExtension(file.name);
//        console.log(file);
        let validExtensions = ["svs", "jpg"];
        if(validExtensions.includes(fileType)){
            if(file){
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
        }

    };
//    console.log("after FOR");

//}

function uploadFile(name, fileOriginalName){
    let xhr = new XMLHttpRequest();
    xhr.open("POST", '/upload');
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
       if(loaded == total){
           progressArea.innerHTML = "";
           let uploadedHTML = `
                <li class="row">
                    <div class="content">
                        <img src="./static/logo/file.png">
                         <div class="details">
                            <span class="name">${name} • Uploading</span>
                            <span class="size">${fileSize}</span>
                        </div>
                    </div>
                    <img src="./static/logo/load.gif">
                `;
                uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);

            var myTimeout = setTimeout(function run(){
                            let req = myGreeting(fileOriginalName);
                            if (req === false) {
                                setTimeout(run, 1000);
                            }
                       }, 5000);
       }
    });
    let formData = new FormData(form);
    xhr.send(formData);
};
