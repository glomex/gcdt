var l33t = require('1337')


exports.handler = function(event, context, callback) {
    console.log( "event", event );

    if (typeof(event.ramuda_action) !== "undefined" && event.ramuda_action == "ping") {
        console.log("respond to ping event");
        callback(null, "alive");
    } else {
        console.log(l33t('glomex rocks!'));  // 910m3x r0ck5!
        callback();  // success
    }
};
