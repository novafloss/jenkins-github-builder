import asyncio
import base64
from datetime import datetime, timedelta, timezone

from asynctest import patch, CoroutineMock, Mock
import pytest


@patch('jenkins_epo.github.GITHUB')
def test_threshold_not_hit(GITHUB, SETTINGS):
    from jenkins_epo.github import check_rate_limit_threshold

    SETTINGS.RATE_LIMIT_THRESHOLD = 3000
    GITHUB.x_ratelimit_remaining = 5000

    check_rate_limit_threshold()


@patch('jenkins_epo.github.GITHUB')
def test_threshold_reenter(GITHUB, SETTINGS):
    from jenkins_epo.github import check_rate_limit_threshold

    SETTINGS.RATE_LIMIT_THRESHOLD = 3000
    GITHUB.x_ratelimit_remaining = 2999

    def get_sideeffect():
        GITHUB.x_ratelimit_remaining = 5000
    GITHUB.rate_limit.get.side_effect = get_sideeffect

    check_rate_limit_threshold()


@patch('jenkins_epo.github.GITHUB')
def test_threshold_hit(GITHUB, SETTINGS):
    from jenkins_epo.github import check_rate_limit_threshold, ApiError

    SETTINGS.RATE_LIMIT_THRESHOLD = 3000
    GITHUB.x_ratelimit_remaining = 2999

    with pytest.raises(ApiError):
        check_rate_limit_threshold()


@patch('jenkins_epo.github.CustomGitHub._process_resp')
@patch('jenkins_epo.github.build_opener')
def test_log_reset(build_opener, _process_resp):
    from jenkins_epo.github import CustomGitHub

    GITHUB = CustomGitHub()
    GITHUB.x_ratelimit_remaining = 4000

    def process_resp_se(*a, **kw):
        GITHUB.x_ratelimit_remaining += 10
    _process_resp.side_effect = process_resp_se

    GITHUB.user.get()

    assert _process_resp.mock_calls


@pytest.mark.asyncio
@asyncio.coroutine
def test_log_reset_async(mocker):
    _process_resp = mocker.patch(
        'jenkins_epo.github.CustomGitHub._process_resp'
    )
    ClientSession = mocker.patch('jenkins_epo.github.aiohttp.ClientSession')

    from jenkins_epo.github import CustomGitHub

    GITHUB = CustomGitHub()
    GITHUB.x_ratelimit_remaining = 4000

    def process_resp_se(*a, **kw):
        GITHUB.x_ratelimit_remaining += 10
    _process_resp.side_effect = process_resp_se

    session = ClientSession.return_value
    session.get = CoroutineMock(name='get')
    resp = session.get.return_value
    resp.status = 200
    resp.content_type = 'application/json'
    resp.json = CoroutineMock(return_value={})

    yield from GITHUB.user.aget()

    assert _process_resp.mock_calls


@pytest.mark.asyncio
def test_aget_dict(mocker):
    from jenkins_epo.github import CustomGitHub

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'json', 'status'])
    session.get = CoroutineMock(return_value=response)
    response.status = 200
    response.content_type = 'application/json'
    response.headers = {'ETag': 'cafed0d0'}
    response.json = CoroutineMock(return_value={'data': 1})
    GITHUB = CustomGitHub(access_token='cafed0d0')
    res = yield from GITHUB.user.aget(per_page='100')

    assert res._headers
    assert 'data' in res


@pytest.mark.asyncio
def test_aget_list(mocker):
    from jenkins_epo.github import CustomGitHub

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'json', 'status'])
    session.get = CoroutineMock(return_value=response)
    response.status = 200
    response.content_type = 'application/json'
    response.headers = {'Etag': 'cafed0d0'}
    response.json = CoroutineMock(return_value=[{'data': 1}])

    GITHUB = CustomGitHub(access_token='cafed0d0')
    res = yield from GITHUB.user.aget()

    assert res._headers
    assert 'data' in res[0]


@pytest.mark.asyncio
def test_aget_html(mocker):
    from jenkins_epo.github import CustomGitHub

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'read', 'status'])
    session.get = CoroutineMock(return_value=response)
    response.status = 200
    response.content_type = 'text/html'
    response.headers = {'ETag': 'cafed0d0'}
    response.read = CoroutineMock(return_value='<!DOCTYPE')

    GITHUB = CustomGitHub(access_token='cafed0d0')
    with pytest.raises(Exception):
        yield from GITHUB.user.aget()

    assert response.read.mock_calls


@pytest.mark.asyncio
def test_aget_404(mocker):
    from jenkins_epo.github import CustomGitHub, ApiNotFoundError

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'json', 'status'])
    session.get = CoroutineMock(return_value=response)
    response.status = 404
    response.content_type = 'application/json'
    response.headers = {'ETag': 'cafed0d0'}
    response.json = CoroutineMock(return_value={'message': 'Not found'})

    GITHUB = CustomGitHub(access_token='cafed0d0')

    with pytest.raises(ApiNotFoundError):
        yield from GITHUB.user.aget()


@pytest.mark.asyncio
def test_aget_304(mocker):
    from jenkins_epo.github import CustomGitHub, ApiError

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'json', 'status'])
    session.get = CoroutineMock(return_value=response)
    response.status = 304
    response.content_type = 'application/json'
    response.headers = {'ETag': 'cafed0d0'}
    response.json = CoroutineMock(return_value={'message': 'Not found'})

    GITHUB = CustomGitHub(access_token='cafed0d0')

    with pytest.raises(ApiError):
        yield from GITHUB.user.aget()


@pytest.mark.asyncio
def test_aget_422(mocker):
    from jenkins_epo.github import CustomGitHub, ApiError

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'json', 'status'])
    session.get = CoroutineMock(return_value=response)
    response.status = 422
    response.headers = {}
    response.content_type = 'application/json'
    response.json = CoroutineMock(
        return_value={'errors': [{'message': 'Pouet'}]},
    )

    GITHUB = CustomGitHub(access_token='cafed0d0')

    with pytest.raises(ApiError):
        yield from GITHUB.user.aget()


@pytest.mark.asyncio
@asyncio.coroutine
def test_apost(mocker):
    from jenkins_epo.github import CustomGitHub, ApiError

    aiohttp = mocker.patch('jenkins_epo.github.aiohttp')
    session = aiohttp.ClientSession.return_value
    response = Mock(spec=['headers', 'json', 'status'])
    session.post = CoroutineMock(return_value=response)
    response.status = 304
    response.content_type = 'application/json'
    response.headers = {'ETag': 'cafed0d0'}
    response.json = CoroutineMock(return_value={'message': 'Not found'})

    GITHUB = CustomGitHub(access_token='cafed0d0')

    with pytest.raises(ApiError):
        yield from GITHUB.user.apost(pouet=True)


@pytest.mark.asyncio
@patch('jenkins_epo.github.GITHUB')
@patch('jenkins_epo.github.CACHE')
def test_cached_arequest_miss(CACHE, GITHUB, SETTINGS):
    SETTINGS.GITHUB_TOKEN = 'cafec4e3e'
    GITHUB.x_ratelimit_remaining = -1
    from jenkins_epo.github import cached_arequest

    CACHE.get.side_effect = KeyError('key')

    query = Mock(aget=CoroutineMock(return_value='plop'))
    ret = yield from cached_arequest(query)

    assert 'plop' == ret


@pytest.mark.asyncio
@patch('jenkins_epo.github.GITHUB')
@patch('jenkins_epo.github.CACHE')
def test_cached_arequest_no_cache_hit_valid(CACHE, GITHUB, SETTINGS):
    SETTINGS.GITHUB_TOKEN = 'cafec4e3e'
    GITHUB.x_ratelimit_remaining = -1
    from jenkins_epo.github import ApiError, cached_arequest

    cached_data = Mock(_headers={'Etag': 'etagsha'})
    CACHE.get.return_value = cached_data

    query = Mock(aget=CoroutineMock(
        side_effect=ApiError('url', request={}, response=dict(code=304))
    ))
    ret = yield from cached_arequest(query)

    assert cached_data == ret


@pytest.mark.asyncio
@patch('jenkins_epo.github.GITHUB')
@patch('jenkins_epo.github.CACHE')
def test_cached_arequest_error(CACHE, GITHUB, SETTINGS):
    SETTINGS.GITHUB_TOKEN = 'cafec4e3e'
    GITHUB.x_ratelimit_remaining = -1
    from jenkins_epo.github import ApiError, cached_arequest

    CACHE.get.side_effect = KeyError('pouet')

    query = Mock(aget=CoroutineMock(
        side_effect=ApiError('url', request={}, response=dict(code=500))
    ))
    with pytest.raises(ApiError):
        yield from cached_arequest(query)


@pytest.mark.asyncio
@asyncio.coroutine
def test_fetch_file_contents(SETTINGS, mocker):
    cached_arequest = mocker.patch(
        'jenkins_epo.github.cached_arequest', CoroutineMock()
    )

    cached_arequest.return_value = dict(content=base64.b64encode(b'{}'))
    from jenkins_epo.github import GITHUB

    contents = yield from GITHUB.fetch_file_contents(Mock(), '/jenkins.yml')

    assert contents == '{}'
    assert cached_arequest.mock_calls


def test_wait_rate_limit(mocker, SETTINGS):
    sleep = mocker.patch('jenkins_epo.github.time.sleep')
    GITHUB = mocker.patch('jenkins_epo.github.GITHUB')
    from jenkins_epo.github import wait_rate_limit_reset

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    GITHUB.x_ratelimit_reset = (now + timedelta(seconds=500)).timestamp()
    GITHUB.x_ratelimit_remaining = 0

    waited_seconds = wait_rate_limit_reset(now)

    assert sleep.mock_calls
    assert waited_seconds > 500.


def test_wait_rate_limit_reenter(mocker, SETTINGS):
    sleep = mocker.patch('jenkins_epo.github.time.sleep')
    GITHUB = mocker.patch('jenkins_epo.github.GITHUB')
    from jenkins_epo.github import wait_rate_limit_reset

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    GITHUB.x_ratelimit_reset = (now - timedelta(seconds=1)).timestamp()
    GITHUB.x_ratelimit_remaining = 0

    waited_seconds = wait_rate_limit_reset(now)

    assert not sleep.mock_calls
    assert 0 == waited_seconds


@pytest.mark.asyncio
@asyncio.coroutine
def test_unpaginate(mocker):
    cached_arequest = mocker.patch(
        'jenkins_epo.github.cached_arequest', CoroutineMock()
    )
    cached_arequest.side_effect = [
        Mock(_headers=dict(Link='<next_url>; rel="next"')),
        Mock(_headers=dict(Link='<prev_url>; rel="prev"'))
    ]
    from jenkins_epo.github import unpaginate

    yield from unpaginate(Mock())

    assert 2 == len(cached_arequest.mock_calls)
