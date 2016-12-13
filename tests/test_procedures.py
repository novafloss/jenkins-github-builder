from unittest.mock import Mock, patch

from aiohttp.test_utils import make_mocked_coro
import pytest


@pytest.mark.asyncio
def test_whoami(mocker):
    mocker.patch(
        'jenkins_epo.procedures.cached_arequest',
        make_mocked_coro(return_value=dict(login='aramis')),
    )

    from jenkins_epo import procedures

    login = yield from procedures.whoami()

    assert 'aramis' == login


@patch('jenkins_epo.procedures.Repository.from_name')
def test_list_repositories(from_name, SETTINGS):
    from jenkins_epo import procedures

    SETTINGS.REPOSITORIES = "owner/repo1,owner/repo1"
    repositories = procedures.list_repositories()
    assert 1 == len(list(repositories))


@patch('jenkins_epo.procedures.Repository.from_name')
def test_list_repositories_from_envvar_404(from_name, SETTINGS):
    from jenkins_epo import procedures

    SETTINGS.REPOSITORIES = "owner/repo1 owner/repo1"
    from_name.side_effect = Exception('404')

    repositories = procedures.list_repositories()

    assert 0 == len(list(repositories))


@patch('jenkins_epo.procedures.list_repositories')
def test_iter_heads_order(list_repositories):
    from jenkins_epo.procedures import iter_heads

    a = Mock()
    branch = Mock(token='a/branch')
    branch.sort_key.return_value = False, 100, 'master'
    a.process_protected_branches.return_value = [branch]
    pr = Mock(token='a/pr')
    pr.sort_key.return_value = False, 50, 'feature'
    a.process_pull_requests.return_value = [pr]
    b = Mock()
    branch = Mock(token='b/branch')
    branch.sort_key.return_value = False, 100, 'master'
    b.process_protected_branches.return_value = [branch]
    pr1 = Mock(token='b/pr1')
    pr1.sort_key.return_value = False, 50, 'feature'
    pr2 = Mock(token='b/pr2')
    pr2.sort_key.return_value = True, 50, 'hotfix'
    b.process_pull_requests.return_value = [pr1, pr2]
    c = Mock()
    c.process_protected_branches.return_value = []
    c.process_pull_requests.return_value = []

    list_repositories.return_value = [a, b, c]

    computed = [h.token for h in iter_heads()]
    wanted = ['a/branch', 'b/pr2', 'a/pr', 'b/branch', 'b/pr1']

    assert wanted == computed


@patch('jenkins_epo.procedures.list_repositories')
def test_iter_heads_close_first(list_repositories):
    from jenkins_epo.procedures import iter_heads

    repo = Mock()
    repo.process_pull_requests.return_value = []
    list_repositories.return_value = [repo]
    branch = Mock(token='repo/branch')
    branch.sort_key.return_value = False, 100, 'master'
    repo.process_protected_branches.return_value = [branch]

    iterator = iter_heads()
    next(iterator)
    iterator.close()


@patch('jenkins_epo.procedures.list_repositories')
def test_iter_heads_close_next(list_repositories):
    from jenkins_epo.procedures import iter_heads

    repo = Mock()
    repo.process_pull_requests.return_value = []
    list_repositories.return_value = [repo]
    master = Mock(token='repo/master')
    master.sort_key.return_value = False, 100, 'master'
    branch = Mock(token='repo/master')
    branch.sort_key.return_value = False, 100, 'master'
    repo.process_protected_branches.return_value = [master, branch]

    iterator = iter_heads()
    next(iterator)
    next(iterator)
    iterator.close()
