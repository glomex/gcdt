import utilities.InfraUtilities

// if a pull request is merged into develop this job bumps the dev level version
// and releases a dev version to PyPi for testing

environ = InfraUtilities.getEnv()
def branchToCheckout = InfraUtilities.getBranch()

out.println(branchToCheckout)

def credentialsToCheckout = "github-jenkins_username-password"
def baseFolder = "infrastructure/jenkins"
def buildScript = baseFolder + "/scripts/build_develop.sh"

def packageName = 'gcdt'
def jobName = "gcdt/gcdt/" + packageName + "-bump-patch-level"
def repository = "glomex/gcdt"

folder("gcdt/gcdt") {
}


job(jobName) {
    environmentVariables {
        keepSystemVariables(true)
        keepBuildVariables(true)
        env('ENV', environ)
        env('PACKAGE_NAME', packageName)
        env('PYTHONUNBUFFERED', "1")
        env('AWS_DEFAULT_REGION', 'eu-west-1')
        // http://chase-seibert.github.io/blog/2014/01/12/python-unicode-console-output.html
        env('PYTHONIOENCODING', 'UTF-8')
    }

    scm {
        git {
            remote {
                github(repository, 'https')
                credentials(credentialsToCheckout)
                branch('develop')
            }

            configure { gitScm ->
                gitScm / 'extensions' << 'hudson.plugins.git.extensions.impl.UserExclusion' {
                    excludedUsers('Jenkins Continuous Integration Server')
                }
            }
        }
    }

    triggers {
        githubPush()
    }
    
    publishers {
        git {
            pushOnlyIfSuccess()
            branch('origin', 'develop')
        }
    }

    wrappers {
        preBuildCleanup()
        colorizeOutput()
    }

    steps {
        shell(readFileFromWorkspace(buildScript))
    }
}
