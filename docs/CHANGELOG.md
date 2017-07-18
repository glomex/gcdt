# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).


## [0.1.420] - 2017-07-18
### Added
- kumo add SNS notifications (#185)
- logcapture mecahnism for tests (#285)
### Deprecated
- kumo "cloudformation" config section, use "parameters" & "stack" instead (#337)

## [0.1.419] - 2017-07-17
### Added
- kumo add status message for empty changeset (#126)

## [0.1.418] - 2017-07-17
### Added
- ramuda & tenkai settings files - json format (#295)

## [0.1.417] - 2017-07-13
### Added
- getting started guide (#312)

## [0.1.415] - 2017-07-12
### Fixed
- kumo update when using the artifactBucket setting (#332)

## [0.1.413] - 2017-07-07
### Added
- ramuda logs command (#247)

## [0.1.412] - 2017-07-05
### Added
- fix some docu issues for ramuda

## [0.1.411] - 2017-07-04
### Added
- configure cloudwatch logs for ramuda (#191)

## [0.1.410] - 2017-07-03
### Fixed
- fix 'file://' prefix for ramuda invoke payload (#246)

## [0.1.409] - 2017-07-03
### Added
- use roleARN for kumo delete, too (#162)

## [0.1.408] - 2017-06-30
### Added
- kumo preview for new stack (#73)

## [0.1.407] - 2017-06-30
### Fixed
- do not fail check_gcdt_update when PyPi is down (#313)

## [0.1.406] - 2017-06-30
### Added
- support for AWS Lambda ENV variables (#262)

## [0.1.405] - 2017-06-30
### Fixed
- minor documentation changes for kumo. Better description of usage of a role for CloudFormation (#162)

## [0.1.404] - 2017-06-29
### Added
- handle SIGTERM and SIGINT signals and stop running deployments accordingly (#40)

## [0.1.403] - 2017-06-22
### Added
- define GracefulExit exception (#40)

## [0.1.402] - 2017-06-21
### Fixed
- ramuda redeploy version without changes issue (#145)

## [0.1.401] - 2017-06-20
### Fixed
- kumo artifactBucket handling (#292)

## [0.1.400] - 2017-06-20
### Fixed
- datetime handling (#226)

## [0.1.399] - 2017-06-19
### Fixed
- tenkai clean up /tmp files (#60)

## [0.1.398] - 2017-06-16
### Added
- kumo use special role for cloudformation deployments (#162)

## [0.1.397] - 2017-06-16
### Fixed
- kumo parameter diffing without params fails (#64)
- kumo parameter diffing flaws (#184)

## [0.1.396] - 2017-06-12
### Added
- ramuda invoke command (#246)

## [0.1.394] - 2017-06-09
### Added
- add stack_output.yml to tenkai bundle artifact (#266)

## [0.1.393] - 2017-06-09
### Added
- ramuda works with python3.6

## [0.1.392] - 2017-06-07
### Added
- added some documentation related to gcdt-bundler and AWS Lambda runtimes

## [0.1.391] - 2017-06-02
### Added
- support for nodejs6.10 + python3.6 runtimes
- specify folders (source & target) for tenkai bundles
- ramuda '--keep' option to speed up your dev cycles

## [0.1.390] - 2017-05-31
### Added
- prepare for nodejs6.10 runtime (PR 293)

## [0.1.8] - 2017-04-27
### Added
- improve exception handling (#285)
  plus proper error message for missing config

## [0.1.7] - 2017-04-27
### Added
- check AWS Lambda runtime in ramuda config (#254)

## [0.1.6] - 2017-04-26
### Added
- getLogger helper to be used by gcdt-plugins (#213)

## [0.1.5] - 2017-04-26
### Added
- gcdt plugin version info in version cmd and datadog (#250)
- use gcdt plugins in E2E test lifecycle (#250)

## [0.1.4] - 2017-04-07
### Added
- gcdt package publicly available on PyPi (#250)

## [0.1.0] - 2017-04-05
### Added
- open source on Github (#255)
- moved build jobs to new infra jenkins (#255)
### Changed
- it is now mandatory for gcdt users to maintain plugin dependencies

## [0.0.84] - 2017-03-30
### Added
- support for hooks in cloudformation templates and hookfiles (#218)

## [0.0.83] - 2017-03-29
### Added
- updated gcdt-plugin dependency

## [0.0.82] - 2017-03-29
### Added
- added scaffolding mechanism
- use MIT LICENSE (#253)
### Fixed
- tamed greedy lookup (#258)
- kumo fixed deprecated pre_hook (#259)

## [0.0.81] - 2017-03-24
### Added
- included plugin documentation
- gcdt_config_reader for json config files (#218)
### Fixed
- ramuda bundle includes settings_<env>.conf file (#249)
- minor improvements from code review sessions (#230)
- missing environment is not properly handled (#248)

## [0.0.80] - 2017-03-09
### Fixed
- fixed ramuda vpc config handling (#225)

## [0.0.79] - 2017-03-08
### Fixed
- kumo docu bug (#183)
- servicediscovery timestamp localization issue (#217)
- ramuda bundling issue (#225)

## [0.0.78] - 2017-03-06
### Added
- moved hocon config_reader to plugin (#150)
- split gcdt_lookups plugin from config_reader (#150)
- improved slack plugin (webhooks, consolidated msgs) (#219)
- extracted bundle step into bundler plugin (#150)

## [0.0.77] - 2017-02-20
### Added
- moved to std python logging + activate DEBUG logs via `-v` (#175)
- std. gcdt lifecycle (#152)
- removed glomex_utils as installation dependency (#152)
- cloudformation utilities need awsclient (see kumo documentation) (#152)
- plugin mechanism (#152)
- moved datadog and slack reporting functionality to gcdt-plugins (#152)
- cmd dispatcher + testable main modules + tests (#152)
- migrated boto_session to awsclient (#152)

## [0.0.76] - 2017-01-30
### Added
- ramuda replaced git short hash in target filename with sha256 (#169)
- requirements.txt and settings_<env>.conf optional for ramuda (#114)
- made boto_session a parameter in credstash (#177)

## [0.0.75] - 2017-01-24
### Added
- added gcdt installer (#201)
- gcdt outdated version warning (#155)
- moved docs from README to sphinx / readthedocs (PR194)
- pythonic dependency management (without pip-compile) (#178)
- removed glomex-utils dependency (#178)
### Changed
- moved CHANGELOG.md to docs folder

## [0.0.73] - 2017-01-09
### Fixed
- (#194)

## [0.0.64] - 2016-11-11
### Fixed
- wrong boto client used when getting lambda arn

## [0.0.63] - 2016-11-08
### Fixed
- pre-hook fires before config is read (#165)

## [0.0.62] - 2016-11-07
### Added
- ramuda pre-bundle hooks
### Fixed
- compress bundle.zip in ramuda bundle/deploy

## [0.0.61] - 2016-11-07
### Fixed
- moved build system to infra account (#160)

## [0.0.60] - 2016-10-07
### Added
- kumo now has the visualize cmd. Req. dot installation (#136).
- tenkai now has the slack notifications (#79).- FIX moved tests to pytest to improve cleanup after tests (#119).
- kumo now has parametrized hooks (#34).
### Fixed
- moved tests to pytest to improve cleanup after tests (#119).
- ramuda rollback to previous version.
- kumo Parameter diffing does not work for aws coma-seperated inputs (#77).
- ramuda fail deployment on failing ping (#113).
- moved tests to pytest to improve cleanup after tests (#119).
- speedup tests by use of mocked service calls to AWS services (#151).

## [0.0.57] - 2016-09-23
### Added
- tenkai now supports execution of bash scripts before bundling, can be used to bundle packages at runtime.
### Fixed
- tenkai now returns proper exit codes when deployment fails.

## [0.0.55] - 2016-09-16
### Added
- kumo utils EBS tagging functionality (intended for post hooks)
- kumo now supports host zones as a parameter for creating route53 records

## [0.0.51] - 2016-09-05
### Fixed
- kumo parameter diff now checks if stack has parameters beforehand

## [0.0.45] - 2016-09-01
### Added
- ramuda autowire functionality
- gcdt sends metrics and events to datadog
### Fixed
- yugen will add invoke lambda permission for new paths in existing APIs

## [0.0.35] - 2016-08-29
### Added
- consolidated slack configuration to .gcdt files
- configuration for slack_channel

## [0.0.34] - 2016-08-tbd
### Fixed
- refactored yugen structure to yugen_main and yugen_core
- improved yugen testability and test coverage
- further improved ramuda test coverage

## [0.0.33] - 2016-08-18
### Added
- gcdt pull request builder
### Fixed
- refactored tenkai structure to tenkai_main and tenkai_core
- improved tenkai testability and test coverage
- refactored ramuda structure to ramuda_main and ramuda_core
- improved ramuda testability and test coverage

## [0.0.30] - 2016-08-02
### Added
- refactored kumo structure to kumo_main and kumo_core
- improved kumo testability and test coverage
- Rate limiting when preview with empty changeset (#48)
### Removed
- kumo validate
- kumo scaffold

## [0.0.29] - 2016-07-21
### Added
- bump glomex-utils to 0.0.11
### Fixed
- create_stack was broken

## [0.0.26] - 2016-07-19
### Added
- kumo now supports stack policies, see README for details
- kumo now displays changes in CloudFormation template parameters
### Fixed
- prettify output
- removed debug output
- removed some unnecessary import validations
- kumo will now exit when importing a cloudformation.py not from your current working directory
