import requests

from cohort_back.settings import VOTING_GITLAB


def req_url(method, end, data=None):
    url = VOTING_GITLAB['api_url'] + "/projects/" + VOTING_GITLAB['project_id'] + end

    return getattr(requests, method)(
        url,
        headers={"PRIVATE-TOKEN": VOTING_GITLAB['private_token']},
        data=data)


class AttachmentReturned:
    def __init__(self, **kwargs):
        resp = kwargs.get('resp', None)
        if resp is not None and isinstance(resp, requests.Response):
            res = resp.json()
            self.alt: str = res.get('alt', None)
            self.url: str = res.get('url', None)
            self.full_path: str = res.get('full_path', None)
            self.markdown: str = res.get('markdown', None)
        else:
            self.alt: str = kwargs.get('alt', None)
            self.url: str = kwargs.get('url', None)
            self.full_path: str = kwargs.get('full_path', None)
            self.markdown: str = kwargs.get('markdown', None)


def post_gitlab_attachment(file) -> requests.Response:
    url = f"{VOTING_GITLAB['api_url']}/projects/" \
          f"{VOTING_GITLAB['project_id']}/uploads"
    return requests.post(
        url,
        headers={
            "PRIVATE-TOKEN": VOTING_GITLAB['private_token'],
        },
        files=dict(file=file)
    )


def post_gitlab_issue(data: dict={}):
    url = f"{VOTING_GITLAB['api_url']}/projects/" \
          f"{VOTING_GITLAB['project_id']}/issues"

    return requests.post(
        url,
        headers={"PRIVATE-TOKEN": VOTING_GITLAB['private_token']},
        data=data
    )
