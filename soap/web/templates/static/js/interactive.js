function _captialize(str)
{
    return str.charAt(0).toUpperCase() + str.slice(1);
}
function _ing(str)
{
    return $.trim(str).slice(0, -1) + "ing...";
}

function poll(action) {
    var btn_id = "#" + action
    $(btn_id).html(_captialize(_ing(action)));
    $(btn_id).attr("disabled", true);
    var pjs = progressJs(btn_id)
    pjs.setOptions({
        theme: 'blueOverlayRadiusHalfOpacity',
        overlayMode: true
    });
    pjs.start();

    $.ajax({
        url: "/progress",
        success: function(rv) {
            if (rv.status == "starting") {
                // do nothing
            }
            else if (rv.status == "stopping") {
                $("#danger").html("Stopping...");
                $("#danger").attr("disabled", true);
            }
            else if (rv.status == "working") {
                $("#danger").html("Stop");
                $("#danger").attr("disabled", false);
                console.log(100.0 * rv.step / rv.total);
                progressJs(btn_id).set(100.0 * rv.step / rv.total);
            }
            else if (rv.status == "complete") {
                $("#danger").html("Clear");
                $("#danger").attr("disabled", false);
                $("#div-message").css('display', 'block')
                $("#ta-message").html(rv.result);
            }
            else {
                alert(rv.error);
            }
            if (rv.status == "complete" || rv.status == "error") {
                $(btn_id).html(_captialize(action));
                $(btn_id).attr("disabled", false);
                $("#danger").html("Clear");
                $("#danger").attr("disabled", false);
                progressJs(btn_id).end();
            }
            if (rv.status == "starting" || rv.status == "working" ||
                rv.status == "stopping") {
                setTimeout(function () { poll(action); }, 500);
            }
        },
        dataType: "json",
        timeout: 5000
    });
}

function run(action) {
    var code = $("#code").val();
    var jstr = JSON.stringify({
        action: action,
        code: code,
    })
    $.ajax({
        url: "/run",
        type: "POST",
        data: jstr,
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function() { poll(action); },
        timeout: 5000
    });
}

function danger() {
    var id = "#danger"
    if ($(id).html() == "Stop")
    {
        $(id).html("Stopping...");
        $(id).attr("disabled", true);
        $.ajax({
            url: "/stop",
            success: function() { },
            dataType: "json",
            timeout: 5000
        });
    }
    else
        $("#code").html("");
}
