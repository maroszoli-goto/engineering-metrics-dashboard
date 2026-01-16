"""
Unit tests for collect_data.py helper functions

Tests cover:
- Username mapping (GitHub to Jira)
- New format (members list with github/jira dict)
- Old format (parallel github.members and jira.members lists)
- Edge cases (missing users, empty teams, None inputs)
"""
import pytest
from collect_data import map_github_to_jira_username


class TestMapGithubToJiraUsername:
    """Tests for map_github_to_jira_username function"""

    def test_new_format_finds_matching_user(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'members': [
                    {'github': 'alice', 'jira': 'alice.jira'},
                    {'github': 'bob', 'jira': 'bob.jira'}
                ]
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert
        assert jira_username == 'alice.jira'

    def test_old_format_finds_matching_user_by_index(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': ['alice', 'bob', 'charlie']
                },
                'jira': {
                    'members': ['alice.jira', 'bob.jira', 'charlie.jira']
                }
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('bob', teams)

        # Assert
        assert jira_username == 'bob.jira'

    def test_returns_none_when_user_not_found(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': ['alice', 'bob']
                },
                'jira': {
                    'members': ['alice.jira', 'bob.jira']
                }
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('nonexistent', teams)

        # Assert
        assert jira_username is None

    def test_searches_multiple_teams(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': ['alice', 'bob']
                },
                'jira': {
                    'members': ['alice.jira', 'bob.jira']
                }
            },
            {
                'name': 'Frontend',
                'github': {
                    'members': ['charlie', 'david']
                },
                'jira': {
                    'members': ['charlie.jira', 'david.jira']
                }
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('charlie', teams)

        # Assert
        assert jira_username == 'charlie.jira'

    def test_empty_teams_list_returns_none(self):
        # Arrange
        teams = []

        # Act
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert
        assert jira_username is None

    def test_team_missing_jira_members_returns_none(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': ['alice', 'bob']
                }
                # jira section missing
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert
        assert jira_username is None

    def test_index_out_of_range_in_old_format_returns_none(self):
        # Arrange - GitHub has 3 members but Jira only has 2
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': ['alice', 'bob', 'charlie']
                },
                'jira': {
                    'members': ['alice.jira', 'bob.jira']
                    # charlie's Jira username missing
                }
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('charlie', teams)

        # Assert
        assert jira_username is None

    def test_new_format_takes_precedence_over_old_format(self):
        # Arrange - Team has both new and old format
        teams = [
            {
                'name': 'Backend',
                'members': [
                    {'github': 'alice', 'jira': 'alice.new.jira'}
                ],
                'github': {
                    'members': ['alice']
                },
                'jira': {
                    'members': ['alice.old.jira']
                }
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert
        # Should use new format
        assert jira_username == 'alice.new.jira'

    def test_case_sensitive_matching(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': ['Alice', 'bob']
                },
                'jira': {
                    'members': ['alice.jira', 'bob.jira']
                }
            }
        ]

        # Act - Search with lowercase
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert - Should not find 'Alice' (case-sensitive)
        assert jira_username is None

    def test_handles_empty_github_members_list(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'github': {
                    'members': []
                },
                'jira': {
                    'members': []
                }
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert
        assert jira_username is None

    def test_new_format_with_missing_jira_key_returns_none(self):
        # Arrange
        teams = [
            {
                'name': 'Backend',
                'members': [
                    {'github': 'alice'}  # Missing 'jira' key
                ]
            }
        ]

        # Act
        jira_username = map_github_to_jira_username('alice', teams)

        # Assert
        assert jira_username is None or jira_username == None

    def test_mixed_format_members_list(self):
        # Arrange - Some members are dicts, some might be strings (edge case)
        teams = [
            {
                'name': 'Backend',
                'members': [
                    {'github': 'alice', 'jira': 'alice.jira'},
                    'bob'  # String instead of dict (malformed)
                ]
            }
        ]

        # Act
        jira_username_alice = map_github_to_jira_username('alice', teams)
        jira_username_bob = map_github_to_jira_username('bob', teams)

        # Assert
        assert jira_username_alice == 'alice.jira'
        assert jira_username_bob is None  # Can't match string format
