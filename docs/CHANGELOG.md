# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.1.396] - 2017-06-12
### Added
- FEATURE ramuda invoke command (#246)

## [0.1.394] - 2017-06-09
### Added
- FEATURE add stack_output.yml to tenkai bundle artifact (#266)

## [0.1.393] - 2017-06-09
### Added
- FEATURE ramuda works with python3.6

## [0.1.392] - 2017-06-07
### Added
- FEATURE added some documentation related to gcdt-bundler and AWS Lambda runtimes

## [0.1.391] - 2017-06-02
### Added
- FEATURE support for nodejs6.10 + python3.6 runtimes
- FEATURE specify folders (source & target) for tenkai bundles
- FEATURE ramuda '--keep' option to speed up your dev cycles

## [0.1.390] - 2017-05-31
### Added
- FEATURE prepare for nodejs6.10 runtime (PR 293)

## [0.1.8] - 2017-04-27
### Added
- FEATURE improve exception handling (#285)
  plus proper error message for missing config

## [0.1.7] - 2017-04-27
### Added
- FEATURE check AWS Lambda runtime in ramuda config (#254)

## [0.1.6] - 2017-04-26
### Added
- FEATURE getLogger helper to be used by gcdt-plugins (#213)

## [0.1.5] - 2017-04-26
### Added
- FEATURE gcdt plugin version info in version cmd and datadog (#250)
- FEATURE use gcdt plugins in E2E test lifecycle (#250)

## [0.1.4] - 2017-04-07
### Added
- FEATURE gcdt package publicly available on PyPi (#250)

## [0.1.0] - 2017-04-05
### Added
- FEATURE open source on Github (#255)
- FEATURE moved build jobs to new infra jenkins (#255)

## [0.0.84] - 2017-03-30
### Added
- FEATURE support for hooks in cloudformation templates and hookfiles (#218)

## [0.0.83] - 2017-03-29
### Added
- FEATURE updated gcdt-plugin dependency

## [0.0.82] - 2017-03-29
### Added
- FEATURE added scaffolding mechanism
- FEATURE use MIT LICENSE (#253)
- FIX tamed greedy lookup (#258)
- FIX kumo fixed deprecated pre_hook (#259)

## [0.0.81] - 2017-03-24
### Added
- FEATURE included plugin documentation
- FIX ramuda bundle includes settings_<env>.conf file (#249)
- FEATURE gcdt_config_reader for json config files (#218)
- FIX minor improvements from code review sessions (#230)
- FIX missing environment is not properly handled (#248)

## [0.0.80] - 2017-03-09
### Added
- FIX fixed ramuda vpc config handling (#225)

## [0.0.79] - 2017-03-08
### Added
- FIX kumo docu bug (#183)
- FIX servicediscovery timestamp localization issue (#217)
- INVESTIGATE ramuda bundling issue (#225)

## [0.0.78] - 2017-03-06
### Added
- FEATURE moved hocon config_reader to plugin (#150)
- FEATURE split gcdt_lookups plugin from config_reader (#150)
- FEATURE improved slack plugin (webhooks, consolidated msgs) (#219)
- FEATURE extracted bundle step into bundler plugin (#150)

## [0.0.77] - 2017-02-20
### Added
- FEATURE moved to std python logging + activate DEBUG logs via `-v` (#175)
- FEATURE std. gcdt lifecycle (#152)
- FEATURE removed glomex_utils as installation dependency (#152)
- FEATURE cloudformation utilities need awsclient (see kumo documentation) (#152)
- FEATURE plugin mechanism (#152)
- FEATURE moved datadog and slack reporting functionality to gcdt-plugins (#152)
- FEATURE cmd dispatcher + testable main modules + tests (#152)
- FEATURE migrated boto_session to awsclient (#152)

## [0.0.76] - 2017-01-30
### Added
- FEATURE ramuda replaced git short hash in target filename with sha256 (#169)
- FEATURE requirements.txt and settings_<env>.conf optional for ramuda (#114)
- FEATURE made boto_session a parameter in credstash (#177)

## [0.0.75] - 2017-01-24
### Added
- FEATURE added gcdt installer (#201)
- FEATURE gcdt outdated version warning (#155)
- FEATURE moved docs from README to sphinx / readthedocs (PR194)
- FEATURE pythonic dependency management (without pip-compile) (#178)
- FEATURE removed glomex-utils dependency (#178)
- FEATURE added CHANGELOG to docs

## [0.0.73] - 2017-01-09
### Added
- FIX (#194)

## [0.0.64] - 2016-11-11
### Added
- FIX wrong boto client used when getting lambda arn

## [0.0.63] - 2016-11-08
### Added
- FIX pre-hook fires before config is read (#165)

## [0.0.62] - 2016-11-07
### Added
- FEATURE ramuda pre-bundle hooks
- FIX compress bundle.zip in ramuda bundle/deploy

## [0.0.61] - 2016-11-07
### Added
- FIX moved build system to infra account (#160)

## [0.0.60] - 2016-10-07
### Added
- FEATURE kumo now has the visualize cmd. Req. dot installation (#136).
- FIX moved tests to pytest to improve cleanup after tests (#119).
- FIX ramuda rollback to previous version.
- FIX kumo Parameter diffing does not work for aws coma-seperated inputs (#77).
- FIX ramuda fail deployment on failing ping (#113).
- FEATURE tenkai now has the slack notifications (#79).- FIX moved tests to pytest to improve cleanup after tests (#119).
- FIX moved tests to pytest to improve cleanup after tests (#119).
- FEATURE kumo now has parametrized hooks (#34).
- FIX speedup tests by use of mocked service calls to AWS services (#151). 

## [0.0.57] - 2016-09-23
### Added
- FEATURE tenkai now supports execution of bash scripts before bundling, can be used
to bundle packages at runtime. 
- FIX tenkai now returns proper exit codes when deployment fails.

## [0.0.55] - 2016-09-16
### Added
- ADD: kumo utils EBS tagging functionality (intended for post hooks)
- FEATURE: kumo now supports host zones as a parameter for creating route53 records

## [0.0.51] - 2016-09-05
### Added
- FIX: kumo parameter diff now checks if stack has parameters beforehand

## [0.0.45] - 2016-09-01
### Added
- ADD: ramuda autowire functionality
- ADD: gcdt sends metrics and events to datadog 
- FIX: yugen will add invoke lambda permission for new paths in existing APIs

## [0.0.35] - 2016-08-29
### Added
- ADD: consolidated slack configuration to .gcdt files
- ADD: configuration for slack_channel

## [0.0.34] - 2016-08-tbd
### Added
- FIX: refactored yugen structure to yugen_main and yugen_core
- FIX: improved yugen testability and test coverage
- FIX: further improved ramuda test coverage

## [0.0.33] - 2016-08-18
### Added
- FIX: refactored tenkai structure to tenkai_main and tenkai_core
- FIX: improved tenkai testability and test coverage
- FIX: refactored ramuda structure to ramuda_main and ramuda_core
- FIX: improved ramuda testability and test coverage
- FEATURE: gcdt pull request builder

## [0.0.30] - 2016-08-02
### Added
- FIX: refactored kumo structure to kumo_main and kumo_core
- FIX: improved kumo testability and test coverage
- FIX: Rate limiting when preview with empty changeset (#48)
### Removed
- FEATURE: kumo validate
- FEATURE: kumo scaffold

## [0.0.29] - 2016-07-21
### Added
- FEATURE: bump glomex-utils to 0.0.11
- FIX: create_stack was broken

## [0.0.26] - 2016-07-19
### Added
- FEATURE: kumo now supports stack policies, see README for details
- FEATURE: kumo now displays changes in CloudFormation template parameters
- FIX: prettify output
- FIX: removed debug output
- FIX: removed some unnecessary import validations
- FIX: kumo will now exit when importing a cloudformation.py not from your current working directory

...
