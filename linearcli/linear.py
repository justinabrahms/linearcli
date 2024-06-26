#!/usr/bin/python3

import sys
from typing import Dict, List, Optional, TypedDict
import json
import os

import requests
from requests import api

from .timing import timing

import argparse

parser = argparse.ArgumentParser(
    prog='linear',
    description='CLI for linear.app',
)

parser.add_argument('--json', action='store_true', help="Print json output")
parser.add_argument('--debug', action='store_true', help="debug mode (for hacking on the thing)")

subparser = parser.add_subparsers(dest='command')

init_parser = subparser.add_parser('init')
init_parser.add_argument('apikey')

sync_parser = subparser.add_parser('sync')
sync_parser.add_argument('what', default='all')

info_parse = subparser.add_parser('info')
info_parse.add_argument('key')

config_parser = subparser.add_parser('config')
config_parser.add_argument('key')
config_parser.add_argument('value')

create_parser = subparser.add_parser('create')
create_parser.add_argument('--title', '-t', required=True)
create_parser.add_argument('--description', '-d', default="")
create_parser.add_argument('--project-id', '-p')
create_parser.add_argument('--team-id')
create_parser.add_argument('--assignee', '-a')
create_parser.add_argument('--state', '-s')
create_parser.add_argument('--labels', '-l')

search_parser = subparser.add_parser('search')
search_parser.add_argument('terms')

PRINT_JSON = False

def send_query(apikey, query) -> dict:
    res = requests.post(
        'https://api.linear.app/graphql',
        json=dict(
            query=query
        ),
        headers={
            "Authorization": apikey
        }
    )
    # print(query)
    assert res.status_code == 200, res.json()
    return res.json()

GET_TEAMS = """
query Teams {
    teams {
        nodes {
            id
            name
        }
    }
}
"""

GET_ME = """
query Me {
    viewer {
        id
    }
}
"""

GET_STATES = """
query States {
    workflowStates(
        filter: {
            team: {
                id: {
                    eq: "<teamId>"
                }
            }
        }
    ) {
        nodes {
            id
            name
            team {
                id
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

GET_USERS = """
query Users {
    users(
        <cursor>
    ) {
        nodes {
            id
            name
            avatarUrl
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

GET_PROJECTS = """
query Projects {
    projects(
        <cursor>
    ){
        nodes {
            id
            name
            teams {
                nodes {
                    id
                }
            }
            slugId
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

SEARCH_ISSUES = """
query Issues {
    issueSearch(
        first: 100,
        query: "<query>"
    ) {
        nodes {
            id
            title
            description
            identifier
            project {
                id
                name
            }
        }
    }
}
"""

ISSUE_INFO = """
query IssueQuery {
  issue(id: "<query>") {
    identifier
    title
    description
    url
  }
}
"""

class Team(TypedDict):
        id: str
        name: str

class State(TypedDict):
    id: str
    name: str
    team: Team

class User(TypedDict):
    id: str
    name: str
    avatarUrl: Optional[str]

class Project(TypedDict):
    id: str
    name: str
    teams: List[Team]
    slugId: str

class Config(TypedDict):
    apikey: str
    teams: List[Team]
    users: List[User]
    projects: List[Project]
    states: List[State]
    teams_to_projects: Dict[str, List[str]]
    projects_by_id: Dict[str, Project]
    states_by_team: Dict[str, Dict[str, str]]
    me: str
    default_team: Optional[str]

def get_config_path():
    os.makedirs(os.path.expanduser("~/.linear/"), exist_ok=True)
    os.makedirs(os.path.expanduser("~/.linear/icons/"), exist_ok=True)
    return os.path.expanduser('~/.linear/data.json')

def load_config() -> Config:
    if not os.path.exists(get_config_path()):
        return {}
    with open(get_config_path(), 'r') as f:
        return json.load(f)

def save_config(config: Config) -> None:
    with open(get_config_path(), 'w') as f:
        json.dump(config, f, indent=4)

def get_icon_path(user_id):
    return os.path.expanduser("~/.linear/icons/") + user_id + ".png"

def download_icon(user_id, url):
    res = requests.get(url)
    with open(get_icon_path(user_id), 'wb') as f:
        f.write(res.content)

def init(apikey:Optional[str] = None, init="all"):
    config = load_config()

    if apikey is None:
        apikey = config['apikey']
    else:
        config['apikey'] = apikey

    if init == "all" or init == "me":
        print("Syncing Me")
        me = send_query(apikey, GET_ME)
        config['me'] = me["data"]["viewer"]["id"]

    if init == "all" or init == "teams":
        print("Syncing Teams")
        teams = send_query(apikey, GET_TEAMS)
        config['teams'] = teams["data"]["teams"]["nodes"]
        if 'default_team' not in config or config['default_team'] is None and len(config['teams']) > 0:
            print("Setting default team to: ", config['teams'][0]["name"], "(", config['teams'][0]['id'], ")")
            print("Change with linearcli config default_team <team_id>")
            config['default_team'] = config['teams'][0]['id']

    if init == "all" or init == "states":
        print("Syncing States")
        states = []
        for team in config['teams']:
            res = send_query(apikey, GET_STATES.replace("<teamId>", team["id"]))
            states.extend(res["data"]["workflowStates"]["nodes"])
        config['states'] = states
        states_by_team = {}
        for state in states:
            team_id = state["team"]["id"]
            if team_id not in states_by_team:
                states_by_team[team_id] = {}
            states_by_team[team_id][state["name"]] = state["id"]
        config["states_by_team"] = states_by_team

    if init == "all" or init == "users":
        print("Syncing Users")
        users = []
        cursor = "first: 100"
        while cursor:
            res = send_query(apikey, GET_USERS.replace("<cursor>", cursor))
            has_next_page = res["data"]["users"]["pageInfo"]["hasNextPage"]
            users.extend(res["data"]["users"]["nodes"])
            if has_next_page:
                cursor = f"first: 100, after: \"{res['data']['users']['pageInfo']['endCursor']}\""
            else:
                cursor = None
        config["users"] = users

    if init == "all" or init == "avatars":
        for user in config["users"]:
            if user["avatarUrl"] is None:
                continue
            download_icon(user["id"], user["avatarUrl"])

    if init == "all" or init == "projects":
        print("Syncing Projects")
        projects = []
        cursor = "first: 100"
        while cursor:
            res = send_query(apikey, GET_PROJECTS.replace("<cursor>", cursor))
            has_next_page = res["data"]["projects"]["pageInfo"]["hasNextPage"]
            projects.extend(res["data"]["projects"]["nodes"])
            if has_next_page:
                cursor = f"first: 100, after: \"{res['data']['projects']['pageInfo']['endCursor']}\""
            else:
                cursor = None

        teams_to_projects = {}
        projects_by_id = {}
        for project in projects:
            projects_by_id[project["id"]] = project
            for team in project["teams"]["nodes"]:
                teams_to_projects[team["id"]] = teams_to_projects.get(team["id"], [])
                teams_to_projects[team["id"]].append(project["id"])
        config["projects"] = projects
        config["teams_to_projects"] = teams_to_projects
        config["projects_by_id"] = projects_by_id

    save_config(config)

def set_config(key: str, value: str):
    config = load_config()
    config[key] = value
    save_config(config)

def create_issue(config, title, project_id=None, team_id=None, assignee_id=None, state_id=None, description="Created by miscript", labels=None, debug=False):
    if team_id is None:
        team_id = config["default_team"]

    if state_id is None:
        state_id = config["states_by_team"][team_id]["Todo"]

    project_part = f"projectId: \"{project_id}\"" if project_id else ""
    assignee_part = ""

    if assignee_id == 'me':
        assignee_part = f'assigneeId: "{config["me"]}"'

    query = f"""
    mutation IssueCreate {{
        issueCreate(
            input: {{
                title: "{title}"
                description: "{description}"
                teamId: "{team_id}"
                stateId: "{state_id}"
                {assignee_part}
                {project_part}
            }}
        ) {{
            success
            issue {{
                id
                title
                identifier
                url
            }}
        }}
    }}
    """
    with timing("create issue", debug=debug):
        res = send_query(config['apikey'], query)
    issue = res["data"]["issueCreate"]["issue"]
    issue_id = issue['id']
    url = issue["url"]

    if labels is not None and len(labels) > 0:
        quoted = ['"%s"' % x for x in labels.split(',')]
        joined = ','.join(quoted)
        label_query = """query Query {issueLabels(filter: { name: { in: [<>] } }) {nodes {id name}}}""".replace("<>", joined)
        with timing("label query", debug=debug):
            label_resp = send_query(config['apikey'], label_query)
        ids = [x['id'] for x in label_resp['data']['issueLabels']['nodes']]

        add_query = 'mutation IssueAddLabel { %s }' % (
            '\n'.join(["""label%d: issueAddLabel(labelId: "%s", id: "%s") { success }""" % (i, label_id, issue_id) for (i, label_id) in enumerate(ids)])
        )
        with timing("label addition", debug=debug):
            try:
                send_query(config['apikey'], add_query)
            except Exception as e:
                print("Couldn't add label: ", e)

    return url


def main():
    args = parser.parse_args(sys.argv[1:])
    command = args.command
    if command is None:
        parser.print_help()
        return sys.exit(1)


    # May be an empty object if the config isn't there.
    config = load_config()

    if command == 'init':
        return init(*args)

    if config["apikey"] is None:
        print("No apikey found. Please run 'linearcli init [apikey]'")
        return

    apikey = config['apikey']

    match command:
        case 'sync':
            init(None, *args)
        case 'config':
            set_config(*args)
        case 'create':
            url = create_issue(
                config,
                args.title,
                project_id=args.project_id,
                team_id=args.team_id,
                assignee_id=args.assignee,
                state_id=args.state,
                description=args.description,
                labels=args.labels,
                debug=args.debug,
            )
            print(url)

        case "listteams":
            teams = config["teams"]
            items = []
            for team in teams:
                items.append({
                    "uid": team["id"],
                    "title": team["name"],
                    "arg": team["id"],
                })
            print(json.dumps({"items": items}, indent=4))

        case "listprojectsforteam":
            team_id = args.pop(0)
            projects = config["teams_to_projects"][team_id]
            items = []
            for project_id in projects:
                project = config["projects_by_id"][project_id]
                items.append({
                    "uid": project["id"],
                    "title": project["name"],
                    "arg": project["id"],
                })
            print(json.dumps({"items": items}, indent=4))

        case "listprojectslugs":
            items = []
            for project in config["projects"]:
                items.append({
                    "uid": project["id"],
                    "title": project["name"],
                    "arg": project["slugId"],
                })
            print(json.dumps({"items": items}, indent=4))

        case "listusers":
            users = config["users"]
            items = []
            for user in users:
                items.append({
                    "uid": user["id"],
                    "title": user["name"],
                    "arg": user["id"],
                    "icon": {
                        "path": get_icon_path(user["id"]),
                    }
                })
            print(json.dumps({"items": items}, indent=4))

        case "search":
            query = args.terms

            results = send_query(apikey, SEARCH_ISSUES.replace("<query>", query))
            issues = []
            for issue in results["data"]["issueSearch"]["nodes"]:
                project = "No Project"
                if issue["project"] and issue["project"]["name"]:
                    project = issue["project"]["name"]
                issues.append({
                    "uid": issue["id"],
                    "title": issue["title"],
                    "subtitle": project + " " + str(issue["description"] if issue["description"] else ""),
                    "arg": issue["identifier"],
                })


            if PRINT_JSON:
                print(json.dumps({"items": issues, "query": query}, indent=4))
            else:
                for item in issues:
                    print(f"{item['arg']} {item['title']}")

        case "info":
            issue_id = args.key
            query = ISSUE_INFO.replace("<query>", issue_id)
            results = send_query(apikey, query)
            issue = results['data']['issue']
            print(f"{issue['identifier']} {issue['title']}")
            print()
            print(issue['description'])
            print()
            print(issue['url'])

if __name__ == '__main__':
    main()
