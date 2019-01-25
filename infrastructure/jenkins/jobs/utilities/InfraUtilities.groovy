package utilities

import groovy.json.JsonSlurper;

public class InfraUtilities {

    // "http://169.254.169.254/latest/dynamic/instance-identity/document"
    private static final String METADATA_URL = "http://169.254.169.254/latest/dynamic/instance-identity/document"
    // TODO: for now I removed the other accounts!
    private static final Map accountMap = [420189626185: 'dev']
    private static final String TEAM_EMAIL = "ops@services.glomex.com"

    public static def getTeamEmail() {
        return TEAM_EMAIL
    }

    public static def getAccountId() throws IOException, MalformedURLException {
        URL url = new URL(METADATA_URL);
        InputStream urlStream = null;

        try {
            urlStream = url.openStream();
            BufferedReader reader = new BufferedReader(new InputStreamReader(urlStream));
            JsonSlurper jsonSlurper = new JsonSlurper();
            Object result = jsonSlurper.parse(reader);
            Map jsonResult = (Map) result;
            String accountid = (String) jsonResult.get("accountId");
            return accountid
        } finally {

        }
    }

    public static def getEnvFromAccountId(String accountId) {
        return accountMap.get(accountId.toLong())
    }

    public static def getEnv() {
        // TODO this does not work on a centralized Jenkins
        // String accountId = getAccountId()
        // return getEnvFromAccountId(accountId)
        return "dev"
    }

    public static def getBranch() {
        Map branchMap = [dev: "develop"]
        String branch = branchMap.get(getEnv())
        return branch
    }

    public static def getSlackChannel() {
        Map channelMap = [dev: "gcdt"]
        String channel = channelMap.get(getEnv())
        return channel
    }
}
