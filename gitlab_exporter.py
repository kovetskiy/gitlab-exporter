#!/usr/bin/env python
# encoding: utf-8

import logging
import os
from datetime import datetime
import time

import gitlab
from prometheus_client import start_http_server, Summary

try:
    loglevel = getattr(logging, os.environ.get('LOGLEVEL', 'WARN').upper())
except AttributeError:
    pass

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(level=loglevel)

# time to sleep between calls to gitlab
INTERVAL = int(os.environ.get('INTERVAL', 300))

# port to listen on
PORT = int(os.environ.get('PORT', 3001))

# URL of the GitLab instance, defaults to hosted GitLab
URL = str(os.environ.get('URL', 'https://gitlab.com'))

# Secret token for the app to authenticate itself
TOKEN = str(os.environ.get('TOKEN'))

# Login to GitLab
gl = gitlab.Gitlab(URL, TOKEN)
gl.auth()

# Initialize Prometheus instrumentation
gitlab_project_build_time = Summary('gitlab_project_build_time', 'Time the project builds took to run', ['project_id', 'project_name', 'stage', 'status'])


def get_projects():
    projects = gl.projects.list()
    return projects


def get_project_builds(project):
    id = project.id
    project_builds = gl.project_builds.list(project_id=id)
    return project_builds


def get_build_time(build):
    try:
        build_start = datetime.strptime(build.started_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        build_end = datetime.strptime(build.finished_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        build_time = build_end - build_start
        return build_time
    except TypeError:
        pass


def get_stats():
    for project in get_projects():
        project = gl.projects.get(project.id)
        for build in get_project_builds(project):
            try:
                build_time = get_build_time(build)
                gitlab_project_build_time.labels(project_id=project.id, project_name=project.name, stage=build.stage, status=build.status).observe(build_time.total_seconds())
            except AttributeError:
                pass


if __name__ == '__main__':
    start_http_server(PORT)
    log.info('listening on port {0}'.format(PORT))
    while True:
        try:
            get_stats()
            log.info('sleeping for {0} seconds'.format(INTERVAL))
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            break
