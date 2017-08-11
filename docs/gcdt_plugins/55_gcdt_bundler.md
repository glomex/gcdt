## gcdt-bundler plugin 

Create code bundles for tenkai and ramuda.


### Related documents



### Sample config

bundling sample for kumo:
``` js
...
"bundling": {
    "folders": [
        { "source" = "./codedeploy", target = "." },
        { "source" = "../app", target = "app" },
        { "source" = "../images", target = "images" },
        { "source" = "../supercars", target = "supercars" }
    ]
}
```

Bundling sample for ramuda:
``` js
...
"bundling": {
  "zip": "bundle.zip",
  "folders": [
    { "source": "./vendored", "target": "."},
    { "source": "./impl", "target": "impl"}
  ]
},
```
