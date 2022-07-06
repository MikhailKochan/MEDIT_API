var container = document.querySelectorAll('.container-table');
//var datetime = container.querySelector('#status');
//status = el.querySelectorAll('#st')

//console.log(container[container.length - 1].querySelector('#status'));
//console.log(container[container.length - 1].querySelector('#datetime'));


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

function getCategoryList(datetime) {
//    console.log(datetime);
    var xhr = new XMLHttpRequest();
    xhr.open("GET", `/get/${datetime}`, false);
    xhr.send();

    // stop the engine while xhr isn't done
    for(; xhr.readyState !== 4;)

    if (xhr.status === 200) {

        console.log('SUCCESS', xhr.responseText);

    } else console.warn('request_error');
    return JSON.parse(xhr.responseText)
}

function progress (container) {
    let datetime = container.querySelector("#datetime").textContent,
     status = container.querySelector('#status'),
     result = container.querySelector('#result'),
     button = container.querySelector(".button"),
     button2 = container.querySelector(".button2");
//    let button = document.querySelector(".button"),
//    button2 = document.querySelector(".button2");
//    console.log(datetime);

    let width = getCategoryList(datetime).split(',');
    console.log(width);
//    let elem = container.querySelector("#progress"),
    let id = setInterval(progressStatus,5000);
    function progressStatus () {
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
//       console.log(typeof width);
//       console.log(width[0]);
      if (parseInt(width[0]) >= 100) {
        clearInterval(id);
        container.querySelector("#datetime").innerHTML = `
        ${datetime.replace(/_/,'/').replace(/_/,'/').replace(/_/,'-').replace(/_/,':')}`;
        status.innerHTML = "";
        status.innerHTML = `
            Done
            <img src="/static/logo/green_check.png">
        `;
        if(button!=null){
            button.style.display = "flex"
        };
        button2.style.display = "flex";
        if(width[1]){
            result.innerHTML = `<b>${width[1]}</b>`
        }
      } else {
        width = getCategoryList(datetime).split(',');
        console.log(width);
        if(width[0] != ""){
        elem.style.width = width[0] + '%';
//        console.log(width[0]);
        percent.textContent = width[0] + '%';}
      else{
        status.innerHTML = 'Process is broken';
        clearInterval(id);
      }}
    }
}

function getWork(container){
    let datetime = container.querySelector("#datetime").textContent,
     status = container.querySelector("#status"),
     button = container.querySelector(".button"),
     button2 = container.querySelector(".button2");
//     console.log(status.textContent);

    if(status.textContent.includes('process')){
//        console.log("In process in if");
//        console.log(status);
//        status.innerHTML = "";
        status.innerHTML = `
        <img src="/static/logo/load.gif">`;
        progress(container);
    }else{
        container.querySelector("#datetime").innerHTML = `
        ${datetime.replace(/_/,'/').replace(/_/,'/').replace(/_/,'-').replace(/_/,':')}`;
//        status.innerHTML = `
//        Done
//        <img src="/static/logo/green_check.png">
//    `;
        button2.style.display = "flex";
        if(button!=null){
            button.style.display = "flex"
        }

    };
    }
for (var i = 1; i < container.length; ++i) {

    getWork(container[i]);
}
//const x = getCategoryList(datetime);


//  progress();