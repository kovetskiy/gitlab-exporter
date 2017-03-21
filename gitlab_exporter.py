#!/usr/bin/env python
# encoding: utf-8

import logging
import os
from datetime import datetime
import time

import gitlab
from prometheus_client import start_http_server, Summary, Gauge

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
projects_total = Gauge('gitlab_projects_total', 'Number of projects')
builds_total = Gauge('gitlab_builds_total', 'Number of builds', ['project_id', 'project_name'])
build_duration_seconds = Summary('gitlab_build_duration_seconds', 'Seconds the build took to run', ['project_id', 'project_name', 'stage', 'status'])
open_issues_total = Gauge('gitlab_open_issues_total', 'Number of open issues', ['project_id', 'project_name'])
pipeline_duration_seconds = Summary('gitlab_pipeline_duration_seconds', 'Seconds the pipeline took to run', ['project_id', 'project_name', 'status'])


def get_projects():
    projects = gl.projects.list(all=True)
    return projects


def get_builds(project):
    builds = project.builds.list()
    return builds


def get_duration(process):
    try:
        start = datetime.strptime(process.started_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        end = datetime.strptime(process.finished_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        duration = end - start
        return duration
    except TypeError:
        return 0


def get_pipelines(project):
    try:
        pipelines = project.pipelines.list()
        return pipelines
    except gitlab.exceptions.GitlabListError:
        return []


def get_stats():
    projects = get_projects()
    projects_total.set(len(projects))
    for project in projects:
        project = gl.projects.get(project.id)
        builds_total.labels(project_id=project.id, project_name=project.name).set(len(project.builds.list()))
        open_issues_total.labels(project_id=project.id, project_name=project.name).set(project.open_issues_count)
        for pipeline in get_pipelines(project):
            try:
                duration = get_duration(pipeline)
                summary = pipeline_duration_seconds.labels(project_id=project.id, project_name=project.name, status=pipeline.status)
                summary.observe(duration.total_seconds())
            except AttributeError:
                pass
        for build in get_builds(project):
            try:
                duration = get_duration(build)
                summary = build_duration_seconds.labels(project_id=project.id, project_name=project.name, stage=build.stage, status=build.status)
                summary.observe(duration.total_seconds())
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
