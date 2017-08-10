## gcdt-lookups plugin

The lookups functionality was previously part of the hocon config reader. The lookup functionality was refactored into this `gcdt-lookups` plugin and with the refactoring we also pinned the functionality it into a dedicated lifecycle step. 


### Related documents

* [credstash](https://github.com/fugue/credstash)


### lookup stack output

The `stack` lookup is used to substitute configuration where the value is an output from another cloudformation stack.

format: `lookup:stack:<stackname>:<output>`
sample: `lookup:secret:slack.token`


### lookup ssl certificate

format: `lookup:ssl:<stackname>:<output>`
sample: `lookup:ssl:*.infra.glomex.coud`
sample: `lookup:ssl:*.infra.glomex.coud`

'ssl' lookup uses the `server_certificate` functionality built into AWS IAM. It is configured default lookup so for each stack also the certificates are added to stackdata.

I possible, please use the new acm lookup!


### lookup acm certificate

format: `lookup:acm:<name_1>:...:<name_n>:`
sample: `lookup:acm:foo.mes.glomex.cloud:supercars.infra.glomex.cloud:*.dev.infra.glomex.cloud`

'acm' lookup uses the AWS ACM (Certificate Manager) functionality. It is configured as default lookup.

Features of the `acm lookup`:

* pass a list of hostnames that should be secured.
* check all certificates in ACM if the configured CN (DomainName) or SANs (SubjectAlternativeNames) (including wildcards) if they match for the given list of hostnames
* the chosen certificates STATUS must be **ISSUED**
* if there are multiple matches, use the one with the most distant expiry date
* return the ARN of the certificate
* wildcards for hosted zone are expressed with "*."
* 'ERROR' in case a certificate matching the specified list of names can not be found


### lookup secret

The `secret` lookup is used to substitute configuration where the value is a password, token or other sensitive information that you can not commit to a repository.  
 
format: `lookup:secret:<name>.<subname>`
sample: `lookup:secret:datadog.api_key`
lookup the 'datadog_api_key' entry from credstash
sample: `lookup:secret:slack.webhook:CONTINUE_IF_NOT_FOUND`
lookup the 'slack.token' entry from credstash

note that the `slack.token` lookup does not fail it the accounts credstash does not have the `slack.token` entry.


### DEPRECATED lookup baseami

The `baseami` lookup is used lookup the baseami for cloudformation infrastructures.
