const dropArea = document.querySelector(".drag-area");
dragText = dropArea.querySelector("header");
button = dropArea.querySelector("button");
input = dropArea.querySelector("input");
//send-btn = document.querySelector("#send-btn");
let files; // this is a global variable and we'll use it inside multiple functions


dropArea.onclick = ()=>{
    input.click();
}

//button.onclick = ()=>{
//    send-btn.click();
//}

input.addEventListener("change", function(){
   file = this.files[0];
   showFiles();
   dropArea.classList.add('active');
});

//if user drag file over DropArea
dropArea.addEventListener("dragover", ()=>{
    event.preventDefault();
    dropArea.classList.add('active');
    dragText.textContent = "Загрузить этот файл";
});

//if user leave dragged file from DropArea
dropArea.addEventListener("dragleave", ()=>{
    dropArea.classList.remove('active');
    dragText.textContent = "Область для загрузки .JPG";
});

//if user drop file on DropArea
dropArea.addEventListener("drop", ()=>{
    event.preventDefault();
    // getting user files anf[0] this means if user select multiples then we'll select only the first one
    file = event.dataTransfer.files[0];
    showFiles();
});

function showFiles(){
    let  fileType = file.type;
    let validExtensions = ["image/jpeg", "image/jpg"]; // add some valid image
    if(validExtensions.includes(fileType)){
        let fileReader = new FileReader();
        console.log(fileReader)// create new reader object
        fileReader.onload = ()=>{
            let fileURL = fileReader.result;
            let imgTag = `<div id="cancel-btn"><i class="fas fa-times"></i></div><img src="${fileURL}" alt="">`; // creating tag img and passing user selected file course inside src attribute
            dropArea.innerHTML = imgTag; // adding that created img
        }
        fileReader.readAsDataURL(file);
    }else{
        alert('This is not an image File');
    }
}