from github import Github
from datetime import datetime, timedelta, timezone
from dateutil import parser
import pandas as pd
from typing import List, Dict, Any


class GitHubCollector:
    def __init__(self, token: str, repositories: List[Dict[str, str]] = None,
                 organization: str = None, teams: List[str] = None, team_members: List[str] = None, days_back: int = 90):
        self.github = Github(token)
        self.repositories = repositories or []
        self.organization = organization
        self.teams = teams or []
        self.team_members = team_members or []
        self.days_back = days_back
        self.since_date = datetime.now(timezone.utc) - timedelta(days=days_back)

    def _get_repositories(self):
        """Get list of repositories to process"""
        repos = []

        # If specific repos are configured, use those
        if self.repositories:
            for repo_config in self.repositories:
                owner = repo_config['owner']
                repo_name = repo_config['repo']
                repos.append(self.github.get_repo(f"{owner}/{repo_name}"))

        # If organization and teams are configured, get repos from those teams
        elif self.organization and self.teams:
            print(f"Fetching repositories for teams: {', '.join(self.teams)}")
            org = self.github.get_organization(self.organization)

            for team_slug in self.teams:
                try:
                    print(f"  Getting repos for team: {team_slug}")
                    team = org.get_team_by_slug(team_slug)
                    team_repos = list(team.get_repos())
                    print(f"    Found {len(team_repos)} repositories")
                    repos.extend(team_repos)
                except Exception as e:
                    print(f"    Error getting team {team_slug}: {e}")
                    continue

            # Remove duplicates
            unique_repos = {repo.full_name: repo for repo in repos}
            repos = list(unique_repos.values())
            print(f"Total unique repositories: {len(repos)}")

        # If organization is configured with team members, find repos they contribute to
        elif self.organization and self.team_members:
            print(f"Finding repositories for {len(self.team_members)} team members in {self.organization}")
            repo_names = set()

            for username in self.team_members:
                try:
                    print(f"  Checking repos for {username}...")
                    user = self.github.get_user(username)

                    # Get user's recent events to find repos they've worked on
                    for event in user.get_events()[:50]:  # Last 50 events
                        if hasattr(event, 'repo') and event.repo:
                            # Only include repos from the target organization
                            if event.repo.full_name.startswith(f"{self.organization}/"):
                                repo_names.add(event.repo.full_name)
                except Exception as e:
                    print(f"  Error getting repos for {username}: {e}")
                    continue

            print(f"Found {len(repo_names)} unique repositories")

            # Get repo objects
            for repo_name in repo_names:
                try:
                    repos.append(self.github.get_repo(repo_name))
                except Exception as e:
                    print(f"  Error accessing {repo_name}: {e}")
                    continue

        # Fallback: get all repos from org
        elif self.organization:
            print(f"Fetching all repositories from organization: {self.organization}")
            org = self.github.get_organization(self.organization)
            repos = list(org.get_repos())
            print(f"Found {len(repos)} repositories in {self.organization}")

        return repos

    def collect_all_metrics(self):
        """Collect all metrics for configured repositories"""
        all_data = {
            'pull_requests': [],
            'reviews': [],
            'commits': [],
            'deployments': []
        }

        repos = self._get_repositories()

        for repo in repos:
            print(f"Collecting metrics for {repo.full_name}...")

            try:
                all_data['pull_requests'].extend(self.collect_pr_metrics(repo))
                all_data['reviews'].extend(self.collect_review_metrics(repo))
                all_data['commits'].extend(self.collect_commit_metrics(repo))
                all_data['deployments'].extend(self.collect_deployment_metrics(repo))
            except Exception as e:
                print(f"Error collecting metrics for {repo.full_name}: {e}")
                continue

        # Filter by team members if specified
        if self.team_members:
            all_data = self._filter_by_team_members(all_data)

        return all_data

    def _filter_by_team_members(self, data):
        """Filter data to only include specified team members"""
        filtered_data = {
            'pull_requests': [pr for pr in data['pull_requests']
                            if pr['author'] in self.team_members],
            'reviews': [r for r in data['reviews']
                       if r['reviewer'] in self.team_members or r['pr_author'] in self.team_members],
            'commits': [c for c in data['commits']
                       if c['author'] in self.team_members],
            'deployments': data['deployments']  # Keep all deployments
        }
        return filtered_data

    def collect_pr_metrics(self, repo):
        """Collect pull request metrics"""
        prs = []

        try:
            for pr in repo.get_pulls(state='all', sort='updated', direction='desc'):
                if pr.updated_at < self.since_date:
                    break

                # Limit to recent PRs to avoid rate limiting
                if len(prs) >= 50:
                    break

                try:
                    pr_data = {
                        'repo': repo.full_name,
                        'pr_number': pr.number,
                        'title': pr.title,
                        'author': pr.user.login,
                        'created_at': pr.created_at,
                        'merged_at': pr.merged_at,
                        'closed_at': pr.closed_at,
                        'state': pr.state,
                        'merged': pr.merged,
                        'additions': pr.additions,
                        'deletions': pr.deletions,
                        'changed_files': pr.changed_files,
                        'comments': pr.comments,
                        'review_comments': pr.review_comments,
                        'commits': pr.commits,
                    }

                    # Calculate cycle time (created to merged/closed)
                    if pr.merged_at:
                        pr_data['cycle_time_hours'] = (pr.merged_at - pr.created_at).total_seconds() / 3600
                    elif pr.closed_at:
                        pr_data['cycle_time_hours'] = (pr.closed_at - pr.created_at).total_seconds() / 3600
                    else:
                        pr_data['cycle_time_hours'] = None

                    # Get time to first review
                    try:
                        reviews = list(pr.get_reviews())
                        if reviews:
                            first_review = min(reviews, key=lambda r: r.submitted_at)
                            pr_data['time_to_first_review_hours'] = (
                                first_review.submitted_at - pr.created_at
                            ).total_seconds() / 3600
                        else:
                            pr_data['time_to_first_review_hours'] = None
                    except:
                        pr_data['time_to_first_review_hours'] = None

                    prs.append(pr_data)
                except Exception as e:
                    # Skip individual PRs that fail
                    continue

        except Exception as e:
            print(f"Error collecting PRs for {repo.full_name}: {e}")

        return prs

    def collect_review_metrics(self, repo):
        """Collect code review metrics"""
        reviews = []

        try:
            pr_count = 0
            for pr in repo.get_pulls(state='all', sort='updated', direction='desc'):
                if pr.updated_at < self.since_date:
                    break

                # Limit to recent PRs
                pr_count += 1
                if pr_count > 50:
                    break

                try:
                    for review in pr.get_reviews():
                        reviews.append({
                            'repo': repo.full_name,
                            'pr_number': pr.number,
                            'reviewer': review.user.login,
                            'submitted_at': review.submitted_at,
                            'state': review.state,
                            'pr_author': pr.user.login,
                        })

                    # Also collect review comments
                    for comment in pr.get_review_comments():
                        reviews.append({
                            'repo': repo.full_name,
                            'pr_number': pr.number,
                            'reviewer': comment.user.login,
                            'submitted_at': comment.created_at,
                            'state': 'COMMENTED',
                            'pr_author': pr.user.login,
                        })
                except:
                    # Skip PRs with errors
                    continue

        except Exception as e:
            print(f"Error collecting reviews for {repo.full_name}: {e}")

        return reviews

    def collect_commit_metrics(self, repo):
        """Collect contributor commit metrics"""
        commits = []

        try:
            count = 0
            for commit in repo.get_commits(since=self.since_date):
                # Limit commits to avoid rate limiting
                count += 1
                if count > 100:
                    break

                try:
                    if commit.author:
                        commits.append({
                            'repo': repo.full_name,
                            'sha': commit.sha,
                            'author': commit.author.login if commit.author else 'unknown',
                            'date': commit.commit.author.date,
                            'message': commit.commit.message.split('\n')[0],
                            'additions': commit.stats.additions,
                            'deletions': commit.stats.deletions,
                            'total_changes': commit.stats.total,
                        })
                except:
                    continue

        except Exception as e:
            print(f"Error collecting commits for {repo.full_name}: {e}")

        return commits

    def collect_deployment_metrics(self, repo):
        """Collect deployment metrics"""
        deployments = []

        try:
            for deployment in repo.get_deployments():
                if deployment.created_at < self.since_date:
                    break

                deployments.append({
                    'repo': repo.full_name,
                    'id': deployment.id,
                    'environment': deployment.environment,
                    'created_at': deployment.created_at,
                    'updated_at': deployment.updated_at,
                    'sha': deployment.sha,
                    'ref': deployment.ref,
                })
        except Exception as e:
            print(f"Warning: Could not fetch deployments for {repo.full_name}: {e}")

        return deployments

    def collect_team_metrics(self, team_name: str, team_members: List[str], start_date: datetime = None, end_date: datetime = None):
        """Collect metrics for a specific team

        Args:
            team_name: Name of the team (for labeling)
            team_members: List of GitHub usernames in the team
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Dictionary with team metrics data
        """
        # Temporarily override team members and dates
        original_members = self.team_members
        original_since = self.since_date

        self.team_members = team_members

        if start_date:
            self.since_date = start_date
        if end_date:
            # Store end_date for filtering
            self.end_date = end_date
        else:
            self.end_date = datetime.now(timezone.utc)

        # Collect data
        data = self.collect_all_metrics()

        # Add team label to all data
        for pr in data['pull_requests']:
            pr['team'] = team_name
        for review in data['reviews']:
            review['team'] = team_name
        for commit in data['commits']:
            commit['team'] = team_name

        # Restore original settings
        self.team_members = original_members
        self.since_date = original_since
        if hasattr(self, 'end_date'):
            delattr(self, 'end_date')

        return data

    def collect_person_metrics(self, username: str, start_date: datetime, end_date: datetime):
        """Collect metrics for a specific person in a date range

        Args:
            username: GitHub username
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            Dictionary with person's metrics
        """
        # Temporarily override settings
        original_members = self.team_members
        original_since = self.since_date

        self.team_members = [username]
        self.since_date = start_date
        self.end_date = end_date

        # Collect data
        data = self.collect_all_metrics()

        # Filter by date range (end_date filtering)
        if hasattr(self, 'end_date'):
            data['pull_requests'] = [
                pr for pr in data['pull_requests']
                if pr['created_at'] <= self.end_date
            ]
            data['reviews'] = [
                r for r in data['reviews']
                if r['submitted_at'] <= self.end_date
            ]
            data['commits'] = [
                c for c in data['commits']
                if c['date'] <= self.end_date
            ]

        # Restore original settings
        self.team_members = original_members
        self.since_date = original_since
        if hasattr(self, 'end_date'):
            delattr(self, 'end_date')

        return data

    def calculate_pr_trends(self, df: pd.DataFrame, members: List[str]) -> Dict:
        """Calculate per-person PR trends

        Args:
            df: DataFrame with PR data
            members: List of team member usernames

        Returns:
            Dictionary mapping username to PR statistics
        """
        if df.empty:
            return {member: {'prs': 0, 'merged': 0, 'avg_cycle_time': 0} for member in members}

        trends = {}

        for member in members:
            member_prs = df[df['author'] == member]

            if not member_prs.empty:
                trends[member] = {
                    'prs': len(member_prs),
                    'merged': len(member_prs[member_prs['merged'] == True]),
                    'merge_rate': len(member_prs[member_prs['merged'] == True]) / len(member_prs) if len(member_prs) > 0 else 0,
                    'avg_cycle_time': member_prs['cycle_time_hours'].mean(),
                    'avg_pr_size': (member_prs['additions'] + member_prs['deletions']).mean(),
                    'lines_added': member_prs['additions'].sum(),
                    'lines_deleted': member_prs['deletions'].sum()
                }
            else:
                trends[member] = {
                    'prs': 0,
                    'merged': 0,
                    'merge_rate': 0,
                    'avg_cycle_time': 0,
                    'avg_pr_size': 0,
                    'lines_added': 0,
                    'lines_deleted': 0
                }

        return trends

    def calculate_review_trends(self, df: pd.DataFrame, members: List[str]) -> Dict:
        """Calculate per-person review trends

        Args:
            df: DataFrame with review data
            members: List of team member usernames

        Returns:
            Dictionary mapping username to review statistics
        """
        if df.empty:
            return {member: {'reviews': 0} for member in members}

        trends = {}

        for member in members:
            member_reviews = df[df['reviewer'] == member]

            trends[member] = {
                'reviews': len(member_reviews),
                'prs_reviewed': member_reviews['pr_number'].nunique() if not member_reviews.empty else 0,
            }

        return trends

    def get_dataframes(self):
        """Return all metrics as pandas DataFrames"""
        data = self.collect_all_metrics()

        return {
            'pull_requests': pd.DataFrame(data['pull_requests']),
            'reviews': pd.DataFrame(data['reviews']),
            'commits': pd.DataFrame(data['commits']),
            'deployments': pd.DataFrame(data['deployments']),
        }
