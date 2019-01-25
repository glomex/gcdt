import utilities.InfraUtilities

// this is the pull request builder job


environ = InfraUtilities.getEnv()
def branchToCheckout = InfraUtilities.getBranch()

out.println(branchToCheckout)

def credentialsToCheckout = "github-jenkins_username-password"
def baseFolder = "infrastructure/jenkins"
def artifactBucket = "glomex-infra-reposerver-prod"
def venvScript = baseFolder + "/scripts/prepare_virtualenv.sh"
def buildScript = baseFolder + "/scripts/build_package.sh"
def lifecycleScript = baseFolder + "/scripts/gcdt_lifecycle.sh"

def packageName = 'gcdt'
def jobName = "gcdt/gcdt/" + packageName + "_pull_request"
def repository = "glomex/gcdt"

folder("gcdt/gcdt") {
}

job(jobName) {
    environmentVariables {
        keepSystemVariables(true)
        keepBuildVariables(true)
        env('ENV', environ)
        env('PACKAGE_NAME', packageName)
        env('ARTIFACT_BUCKET', artifactBucket)
        env('PYTHONUNBUFFERED', '1')
        env('AWS_DEFAULT_REGION', 'eu-west-1')
        env('BRANCH', 'develop')
        // http://chase-seibert.github.io/blog/2014/01/12/python-unicode-console-output.html
        env('PYTHONIOENCODING', 'UTF-8')
        // vars specific to gcdt
        env('ACCOUNT', 'infra')
        env('BUCKET', artifactBucket + '/pypi/packages/' + packageName + '/')
    }

    scm {
        git {
            remote {
                github(repository, 'https')
                credentials(credentialsToCheckout)
                branch('${sha1}')
                refspec('+refs/pull/*:refs/remotes/origin/pr/*')
            }
            configure { gitScm ->
                gitScm / 'extensions' << 'hudson.plugins.git.extensions.impl.UserExclusion' {
                    excludedUsers('Jenkins Continuous Integration Server')
                }
            }
        }
    }

    throttleConcurrentBuilds {
        maxTotal(1)
    }

    triggers {
        githubPullRequest {
            // For documentation of settings see source code here:
            // https://github.com/jenkinsci/ghprb-plugin/tree/master/src/main/java/org/jenkinsci/plugins/ghprb/jobdsl
            useGitHubHooks()
            //useGitHubHooks(false)
            //cron('H/5 * * * *')
            orgWhitelist(['glomex'])  // ma_github_org
            onlyTriggerPhrase(false)
            triggerPhrase('@alexa please test')
            permitAll()

            autoCloseFailedPullRequests(false)
            allowMembersOfWhitelistedOrgsAsAdmin(false)
            // whitelist target branch is missing in the config??
            extensions {
                commitStatus {
                    completedStatus('SUCCESS', 'All is well')
                    completedStatus('FAILURE', 'Something went wrong.')
                    completedStatus('PENDING', 'processing...')
                    completedStatus('ERROR', 'Something went wrong!')
                }
            }
        }
    }

    wrappers {
        preBuildCleanup()
        colorizeOutput()

        credentialsBinding {
            usernamePassword('GIT_CREDENTIALS', credentialsToCheckout)
        }
    }

    steps {
        // check env
        shell('''
            echo $ghprbPullId
            if [ -v $ghprbPullId ]
            then
                echo "not inside a pull request - bailing out!"
                exit 1
            fi
              '''.stripIndent())

        // prepare virtualenv
        shell(readFileFromWorkspace(venvScript))

        // run the unit tests
        shell('''
            export PATH=/usr/local/bin:$PATH
            ./venv/bin/python -m pytest --cov gcdt tests/test_*
            '''.stripIndent())

        // run the style checks
        shell('./venv/bin/pylint gcdt || true')

        // build the package and publish to repo server
        shell(readFileFromWorkspace(buildScript))

        // run the gcdt lifecycle 
        shell(readFileFromWorkspace(lifecycleScript))

        // are we done?
        shell("echo 'done done done'")
    }
}
