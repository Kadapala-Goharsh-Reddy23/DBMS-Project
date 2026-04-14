function requestBlood() {

    let name = document.getElementById("name").value;
    let blood = document.getElementById("searchBlood").value;
    let city = document.getElementById("searchCity").value;
    let units = document.getElementById("units").value;

    fetch('/request_blood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, blood, city, units })
    })
    .then(res => res.json())
    .then(data => {
        alert("Request Sent to Admin!");
    });
}

function checkAvailability() {

    let blood = document.getElementById("searchBlood").value;

    fetch(`/availability?blood_group=${blood}`)
    .then(res => res.json())
    .then(data => {

        if (data.length > 0) {
            alert("Available Units: " + data[0].Total_Units);
        } else {
            alert("No stock available");
        }

    });
}