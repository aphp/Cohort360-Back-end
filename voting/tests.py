import random
import string
from io import BytesIO
from unittest.mock import Mock

from django.core.files.uploadedfile import InMemoryUploadedFile
from unittest import mock

from django.utils import timezone
from requests import Response
from rest_framework import status

from cohort_back.settings import VOTING_ATTACHMENT_MAX_SIZE, VOTING_POST_LABELS
from cohort_back.tests import BaseTests
from voting.views import build_full_description, build_error_message

VOTING_URL = "/voting"
ISSUE_CREATE_URL = f"{VOTING_URL}/create-issue"


class MockResponse(Response):
    def __init__(self, data, status_code):
        self._text = data if isinstance(data, str) else None
        self.json_data = data if isinstance(data, dict) else None
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return self._text


def build_basic_file(size: int) -> InMemoryUploadedFile:
    return InMemoryUploadedFile(
        BytesIO(b' ' * (size)), None, 'file.png',
        'image/png', size, None
    )


# FOLDERS
class VotingTests(BaseTests):
    def setUp(self):
        super(VotingTests, self).setUp()


class IssueCreateTests(VotingTests):
    def setUp(self):
        super(IssueCreateTests, self).setUp()

    @mock.patch('voting.views.gitlab')
    def test_create_as_user(self, mock_gitlab: Mock):
        # As a user, I can post an issue
        test_id = 1
        test_state = "opened"
        test_type = "issue"
        test_title = "test"
        test_description = "test"
        test_markdown = "test_markdown"
        full_description = build_full_description(
            test_description, self.user1, test_markdown
        )
        test_label = "Other"
        test_datetime = str(timezone.now())

        mock_gitlab.post_gitlab_attachment.return_value = MockResponse(
            dict(markdown=test_markdown), status_code=status.HTTP_201_CREATED
        )
        test_issue = dict(
                title=test_title,
                id=test_id,
                iid=test_id,
                project_id=test_id,
                description=test_description,
                state=test_state,
                created_at=test_datetime,
                updated_at=test_datetime,
                closed_at=None,
                closed_by=None,
                labels=[test_label],
                type=test_type,
                issue_type=test_type,
                web_url=test_type,
            )
        mock_gitlab.post_gitlab_issue.return_value = MockResponse(
            test_issue, status_code=status.HTTP_201_CREATED
        )

        test_attachment = build_basic_file(VOTING_ATTACHMENT_MAX_SIZE)

        self.client.force_login(self.user1)
        response = self.client.post(ISSUE_CREATE_URL, dict(
            title=test_title,
            description=test_description,
            label=test_label,
            attachment=test_attachment
        ))
        response.render()

        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        mock_gitlab.post_gitlab_attachment.assert_called_once()
        mock_gitlab.post_gitlab_issue.assert_called_once_with(data=dict(
            title=test_title, description=full_description, labels=[test_label]
        ))
        issue = response.json()
        [
            self.assertEqual(test_issue.get(f), issue.get(f))
            for f in issue.keys()
        ]

    @mock.patch('voting.views.gitlab')
    def test_error_create_wrong_data(self, mock_gitlab: Mock):
        # As a user, I cannot post an issue with either empty title,
        # empty description, wrong label or too big a file attached
        wrong_label = ''.join(random.choice(string.ascii_letters)
                              for i in range(10))
        while wrong_label in VOTING_POST_LABELS:
            wrong_label = ''.join(random.choice(string.ascii_letters)
                                  for i in range(10))
        test_title, test_description, test_label = \
            "test_title", "test_description", VOTING_POST_LABELS[0]
        cases = [
            dict(
                title=test_title,
                description=test_description,
                label=VOTING_POST_LABELS[0],
                attachment=build_basic_file(VOTING_ATTACHMENT_MAX_SIZE + 1),
                case_name='attachment_too_big'
            ),
            dict(
                title="",
                description=test_description,
                label=VOTING_POST_LABELS[0],
                attachment=build_basic_file(VOTING_ATTACHMENT_MAX_SIZE),
                case_name='title_empty'
            ),
            dict(
                title=test_title,
                description="",
                label=VOTING_POST_LABELS[0],
                attachment=build_basic_file(VOTING_ATTACHMENT_MAX_SIZE),
                case_name='desc_empty'
            ),
            dict(
                title=test_title,
                description=test_description,
                label=wrong_label,
                attachment=build_basic_file(VOTING_ATTACHMENT_MAX_SIZE),
                case_name='wrong_label'
            ),
        ]

        self.client.force_login(self.user1)
        for case in cases:
            response = self.client.post(ISSUE_CREATE_URL, dict(
                title=case["title"],
                description=case["description"],
                label=case["label"],
                attachment=case["attachment"]
            ))
            response.render()

            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST,
                f"{case['case_name']}: {response.content}"
            )
            mock_gitlab.post_gitlab_attachment.assert_not_called()
            mock_gitlab.post_gitlab_issue.assert_not_called()

    @mock.patch('voting.views.gitlab')
    def test_error_create_not_authenticated(self, mock_gitlab: Mock):
        # As a visitor, I cannot post an issue
        test_title = "test"
        test_description = "test"
        test_label = "Other"

        test_attachment = build_basic_file(VOTING_ATTACHMENT_MAX_SIZE)

        response = self.client.post(ISSUE_CREATE_URL, dict(
            title=test_title,
            description=test_description,
            label=test_label,
            attachment=test_attachment
        ))
        response.render()

        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )
        mock_gitlab.post_gitlab_attachment.assert_not_called()
        mock_gitlab.post_gitlab_issue.assert_not_called()

    @mock.patch('voting.views.gitlab')
    def test_error_gitlab_upload(self, mock_gitlab: Mock):
        # As a user, I am informed if the gitlab server could not be reached
        # while uploading the file attached
        test_title = "test"
        test_description = "test"
        test_label = "Other"
        test_error = "test_erreur"

        mock_gitlab.post_gitlab_attachment.return_value = MockResponse(
            test_error,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        test_attachment = build_basic_file(VOTING_ATTACHMENT_MAX_SIZE)

        self.client.force_login(self.user1)
        response = self.client.post(ISSUE_CREATE_URL, dict(
            title=test_title,
            description=test_description,
            label=test_label,
            attachment=test_attachment
        ))
        response.render()

        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR,
            response.content
        )
        mock_gitlab.post_gitlab_attachment.assert_called_once()
        mock_gitlab.post_gitlab_issue.assert_not_called()
        self.assertEqual(
            response.json().get("message", None),
            build_error_message(
                status.HTTP_500_INTERNAL_SERVER_ERROR, test_error
            )
        )

    @mock.patch('voting.views.gitlab')
    def test_error_gitlab_issue(self, mock_gitlab: Mock):
        # As a user, I am informed if the gitlab server could not be reached
        # while posting the issue
        test_title = "test"
        test_description = "test"
        test_markdown = "test_markdown"
        full_description = build_full_description(
            test_description, self.user1, test_markdown
        )
        test_label = "Other"
        test_error = "test_erreur"

        mock_gitlab.post_gitlab_attachment.return_value = MockResponse(
            dict(markdown=test_markdown), status_code=status.HTTP_201_CREATED
        )
        mock_gitlab.post_gitlab_issue.return_value = MockResponse(
            test_error, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        test_attachment = build_basic_file(VOTING_ATTACHMENT_MAX_SIZE)

        self.client.force_login(self.user1)
        response = self.client.post(ISSUE_CREATE_URL, dict(
            title=test_title,
            description=test_description,
            label=test_label,
            attachment=test_attachment
        ))
        response.render()

        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR,
            response.content
        )
        mock_gitlab.post_gitlab_attachment.assert_called_once()
        mock_gitlab.post_gitlab_issue.assert_called_once_with(data=dict(
            title=test_title, description=full_description, labels=[test_label]
        ))
        self.assertEqual(
            response.json().get("message", None),
            build_error_message(
                status.HTTP_500_INTERNAL_SERVER_ERROR, test_error
            )
        )

