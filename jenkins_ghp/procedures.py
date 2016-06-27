# This file is part of jenkins-ghp
#
# jenkins-ghp is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or any later version.
#
# jenkins-ghp is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# jenkins-ghp.  If not, see <http://www.gnu.org/licenses/>.

import logging

from .github import ApiNotFoundError, GITHUB, cached_request
from .jenkins import JENKINS
from .repository import Branch, PullRequest, Repository
from .settings import SETTINGS
from .utils import match, retry


logger = logging.getLogger('jenkins_ghp')


pr_filter = [p for p in str(SETTINGS.GHP_PR).split(',') if p]


@retry(wait_fixed=15000)
def fetch_settings(repository):
    try:
        ghp_yml = GITHUB.fetch_file_contents(repository, '.github/ghp.yml')
        logger.debug("Loading settings from .github/ghp.yml")
    except ApiNotFoundError:
        ghp_yml = None

    collaborators = cached_request(GITHUB.repos(repository).collaborators)
    branches = cached_request(
        GITHUB.repos(repository).branches, protected='true',
    )

    repository.load_settings(
        branches=branches,
        collaborators=collaborators,
        ghp_yml=ghp_yml,
    )


@retry(wait_fixed=15000)
def list_branches(repository):
    branches = repository.SETTINGS.GHP_BRANCHES
    if not branches:
        logger.debug("No explicit branches configured for %s", repository)
        return []

    for branch in branches:
        logger.debug("Search remote branch %s", branch)
        try:
            ref = cached_request(GITHUB.repos(repository).git(branch))
        except ApiNotFoundError:
            logger.warn("Branch %s not found in %s", branch, repository)
            continue

        sha = ref['object']['sha']
        logger.debug("Fetching commit %s", sha[:7])
        data = cached_request(GITHUB.repos(repository).commits(sha))
        commit = data['commit']
        branch = Branch(repository, ref, commit)
        if branch.is_outdated:
            logger.debug(
                'Skipping branch %s because older than %s weeks',
                branch, repository.SETTINGS.GHP_COMMIT_MAX_WEEKS,
            )
            continue
        yield branch


@retry(wait_fixed=15000)
def list_pulls(repository):
    logger.debug("Querying GitHub for %s PR.", repository)
    try:
        pulls = cached_request(GITHUB.repos(repository).pulls)
    except Exception:
        logger.exception("Failed to list PR for %s.", repository)
        return []

    pulls_o = []
    for data in pulls:
        if not match(data['html_url'], pr_filter):
            logger.debug(
                "Skipping %s (%s).", data['html_url'], data['head']['ref'],
            )
        else:
            pulls_o.append(PullRequest(repository, data))

    for pr in reversed(sorted(pulls_o, key=PullRequest.sort_key)):
        if pr.is_outdated:
            logger.debug(
                'Skipping PR %s because older than %s weeks.',
                pr, SETTINGS.GHP_COMMIT_MAX_WEEKS,
            )
        else:
            yield pr


def list_repositories(with_settings=False):
    repositories = {}
    jobs = JENKINS.get_jobs()

    env_repos = filter(None, SETTINGS.GHP_REPOSITORIES.split(' '))
    for entry in env_repos:
        repository, branches = (entry + ':').split(':', 1)
        owner, name = repository.split('/')
        repositories[repository] = Repository(owner, name)
        logger.debug("Managing %s.", repository)

    for job in jobs:
        for remote in job.get_scm_url():
            repository = Repository.from_remote(remote)
            if repository not in repositories:
                logger.debug("Managing %s.", repository)
                repositories[repository] = repository
            else:
                repository = repositories[repository]

            logger.info("Managing %s.", job)
            repository.jobs.append(job)
            break
        else:
            logger.debug("Skipping %s, no GitHub repository.", job)

    for repo in sorted(repositories.values(), key=str):
        try:
            if with_settings:
                fetch_settings(repo)
            yield repo
        except Exception as e:
            logger.error("Failed to load %s settings: %r", repository, e)


@retry(wait_fixed=15000)
def whoami():
    user = cached_request(GITHUB.user)
    logger.info("I'm @%s on GitHub.", user['login'])
    return user['login']