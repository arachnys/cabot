// extract variables
def env = build.properties['environment']
def branch = env.get('ghprbSourceBranch') ?: env.get('GIT_BRANCH')
// For maestro. should be null -> sha1 manual, and null -> null -> GIT_COMMIT automatic
// For maestro.pr should be null -> sha1 manual, and ghprbActualCommit automatic
// so *should* work in all 4 needed cases
def commit = env.get('ghprbActualCommit') ?: env.get('sha1')
commit = commit ?: env.get('GIT_COMMIT')
def channel = build.workspace.channel
def results = []

branch = branch - ~/^origin\//

// set build name
build.setDisplayName("${commit[0..9]}@${branch}")

println "Building commit: ${commit} from branch ${branch} ..."

// schedule jobs in parallel
println "Scheduling job..."
build('cabot.docker-compose', GIT_BRANCH: branch, GIT_COMMIT: commit)
