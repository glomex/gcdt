'use strict'

exports.handler = (event, context, callback) => {
    if (typeof(event.ramuda_action) !== "undefined" && event.ramuda_action === "ping") {
        context.done(null, "alive")
        return true
    }

    if (typeof(event.ramuda_action) !== "undefined" && event.ramuda_action === "getenv") {
        context.done(null, process.env)
        return true
    }

    console.log('process.env value:')
    console.log(process.env)
}
