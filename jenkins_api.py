
import sys
import os
import ast
import re
import time
import logging
import getpass
import concurrent.futures
import warnings
import textwrap
import xml.etree.ElementTree as ET
import jenkins
import networkx as nx

from datetime_formats import Utility_Time

log = logging.getLogger(__name__)


class Jenkins_API():

    def __init__(self, url, user=getpass.getuser()):

        # From Jenkins version 1.426 onward you can specify an API token instead of your real password.
        # https://docs.cloudbees.com/docs/cloudbees-ci-kb/latest/client-and-managed-masters/how-to-generate-change-an-apitoken

        access_token = os.getenv('JENKIN_ACCESS_TOKEN', None)
        if not access_token:
            log.error("cannot read 'JENKIN_ACCESS_TOKEN' env variable")
            sys.exit(2)

        try:
            # help: https://python-jenkins.readthedocs.io/en/latest/examples.html
            log.info("User '%s' is trying to connect to '%s'", user, url)
            self.server = jenkins.Jenkins(url,
                                          username=user,
                                          password=access_token,
                                          timeout=30)
        except Exception as E:
            log.error("cannot connect to '%s': %s", url, E)
            sys.exit(2)

        try:

            user = self.server.get_whoami()
            full_name = user.get("fullName", None)
            log.info("Username: %s", full_name)

            version = self.server.get_version()
            log.info("Server version: %s", version)

        except Exception as E:

            log.error("connection error:\n%s", E)
            sys.exit(2)


    def get_jobs(self, job_names=None):

        job_name_list = []
        if job_names:
            job_name_list = job_names.split(",")

        jobs = self.server.get_all_jobs()
        log.info("Found '%s' jobs on the server.", len(jobs))

        job_selected = []

        for j in jobs:
            name = j.get("name", None)
            if job_name_list and name not in job_name_list:
                continue
            job_selected.append(j)

        return job_selected


    def get_job_names(self):

        jobs = self.get_jobs(job_names=None)

        job_names = []
        for job in jobs:
            name = job.get("name", None)
            if not name:
                continue
            job_names.append(name)

        job_names.sort()

        return job_names


    def get_views_per_job(self):

        jobs_view_dict = {}
        views_list = self.server.get_views()

        for view_params in views_list:

            view_name = view_params.get("name", None)
            if not view_name:
                continue

            jobs_view = self.server.get_jobs(view_name=view_name)

            for job in jobs_view:

                job_name = job.get("name", None)
                if not job_name:
                    continue

                if job_name not in jobs_view_dict:
                    jobs_view_dict[job_name] = []

                jobs_view_dict[job_name].append(view_name)

        return jobs_view_dict


    def get_job_detail(self, job_name, include_build=True):

        job_details_dict = {}

        try:
            job_info = self.server.get_job_info(job_name)
        except Exception as E:
            log.warning(E)
            return job_details_dict

        jobs_view = self.get_views_per_job()
        view_list = jobs_view.get(job_name, [])
        job_details_dict["view"] = view_list

        # xmlstring = server.get_job_config(job_name)
        # tree = ET.ElementTree(ET.fromstring(xmlstring))
        # job_details_dict["job_config"] = tree

        job_details_dict["displayName"] = job_info.get("displayName", None)
        job_details_dict["fullName"] = job_info.get("fullName", None)

        job_details_dict["description"] = job_info.get("description", None)

        job_details_dict["url"] = job_info.get("url", None)

        job_details_dict["disabled"] = job_info.get("disabled", None)
        job_details_dict["inQueue"] = job_info.get("inQueue", None)

        lastBuild = self.__get_last_build(job_info, "lastBuild")
        lastCompletedBuild = self.__get_last_build(job_info, "lastCompletedBuild")
        lastFailedBuild = self.__get_last_build(job_info, "lastFailedBuild")
        lastStableBuild = self.__get_last_build(job_info, "lastStableBuild")
        lastSuccessfulBuild = self.__get_last_build(job_info, "lastSuccessfulBuild")
        lastUnstableBuild = self.__get_last_build(job_info, "lastUnstableBuild")
        lastUnsuccessfulBuild = self.__get_last_build(job_info, "lastUnsuccessfulBuild")

        job_details_dict["lastBuild"] = lastBuild
        job_details_dict["lastCompletedBuild"] = lastCompletedBuild
        job_details_dict["lastFailedBuild"] = lastFailedBuild
        job_details_dict["lastStableBuild"] = lastStableBuild
        job_details_dict["lastSuccessfulBuild"] = lastSuccessfulBuild
        job_details_dict["lastUnstableBuild"] = lastUnstableBuild
        job_details_dict["lastUnsuccessfulBuild"] = lastUnsuccessfulBuild

        job_details_dict["nextBuildNumber"] = job_info.get("nextBuildNumber", None)

        # TODO: find a more reliable approach to get workspace dir
        workspace_dir = None
        if lastCompletedBuild:
            build_console_output = self.server.get_build_console_output(job_name, lastCompletedBuild)
            if build_console_output:
                match = re.search("Building in workspace (.+)", build_console_output)
                if match:
                    workspace_dir = match.group(1)

        job_details_dict["workspace_dir"] = workspace_dir

        upstreamProjects = job_info.get("upstreamProjects", None)
        job_details_dict["upstreamProjects"] = self.__get_project_names(upstreamProjects)

        downstreamProjects = job_info.get("downstreamProjects", None)
        job_details_dict["downstreamProjects"] = self.__get_project_names(downstreamProjects)

        if include_build:
            self.__get_build(job_name,
                             job_info,
                             job_details_dict)

        return job_details_dict


    def __get_last_build(self, job_info, build_type):

        last_build = job_info.get(build_type, None)
        if not last_build:
            return None

        return last_build.get("number", None)


    def __get_project_names(self, proj_list):

        name_list = []

        if not proj_list:
            return name_list

        for proj in proj_list:
            name = proj.get("name", None)
            if name:
                name_list.append(name)

        return name_list


    def __get_build(self, job_name, job_info, job_details_dict):

        builds = job_info.get("builds", None)
        if not builds:
            return

        job_details_dict["builds"] = {}

        for build in builds:

            number = build.get("number", None)

            if number not in job_details_dict["builds"]:
                job_details_dict["builds"][number] = {}

            # job_details_dict["builds"][number]["build_env"] = server.get_build_env_vars(job_name, number)

            # job_details_dict["builds"][number]["build_test"] = server.get_build_test_report(job_name, number)

            # job_details_dict["builds"][number]["build_console"] = server.get_build_console_output(job_name, number)

            build_info = self.server.get_build_info(job_name, number)

            job_details_dict["builds"][number]["building"] = build_info.get("building", None)

            job_details_dict["builds"][number]["duration"] = build_info.get("duration", None)

            job_details_dict["builds"][number]["result"] = build_info.get("result", None)

            job_details_dict["builds"][number]["url"] = build_info.get("url", None)

            job_details_dict["builds"][number]["timestamp"] = build_info.get("timestamp", None)

            job_details_dict["builds"][number]["build_params"] = self.__get_build_parameters(build_info)

            build_cause = self.__get_build_cause(build_info)
            job_details_dict["builds"][number]["build_cause"] = build_cause

            job_details_dict["builds"][number]["build_cause_list"] = set()

            if build_cause:

                for cause_dict in build_cause:

                    class_name = cause_dict.get("_class", None)
                    if not class_name:
                        continue

                    job_details_dict["builds"][number]["build_cause_list"].add(class_name)


    def __get_build_parameters(self, build_info):

        actions = build_info.get("actions", None)
        if not actions:
            return {}

        parameters = None

        for action in actions:
            class_name = action.get("_class", None)
            if class_name and class_name == "hudson.model.ParametersAction":
                parameters = action.get("parameters", None)
                break

        return parameters


    def __get_build_cause(self, build_info):
        """
            hudson.model.Cause$RemoteCause   --> A build is triggered by another host (REST)
            hudson.model.Cause$UpstreamCause --> A build is triggered by another build (AKA upstream build)
            hudson.model.Cause$UserIdCause   --> A build is started by an user action

            hudson.triggers.SCMTrigger$SCMTriggerCause      --> SCM
            hudson.triggers.TimerTrigger$TimerTriggerCause  --> started by timer

            org.jenkinsci.plugins.gwt.GenericCause  --> Generic Webhook Trigger
            org.jenkinsci.plugins.workflow.support.steps.build.BuildUpstreamCause

            com.cloudbees.jenkins.GitHubPushCause
        """

        actions = build_info.get("actions", None)
        if not actions:
            return {}

        causes = None

        for action in actions:
            class_name = action.get("_class", None)
            if class_name and class_name == "hudson.model.CauseAction":
                causes = action.get("causes", None)
                break

        return causes


    def get_all_jobs_detail(self, include_build=True):

        job_names = self.get_job_names()

        max_threads = 10
        threads = []
        detail_per_job = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="job_detail") as executor:

            for job_name in job_names:

                thread = executor.submit(self.__job_details_run,
                                         job_name,
                                         include_build,
                                         detail_per_job)

                threads.append(thread)

        # Wait for all threads to complete
        concurrent.futures.wait(threads)

        return detail_per_job


    def __job_details_run(self, job_name, include_build, detail_per_job):

        job_dict = self.get_job_detail(job_name, include_build)

        if job_dict:
            detail_per_job[job_name] = job_dict


    def generate_dependency_graph(self, graph_path):
        """
            There might be many jobs running on the Jenkins server, and each has upstream/downstream dependencies.
            Job dependency graph is very helpful in figuring out the relationship between these jobs.

            In the generated graph:
                Green nodes are nightly runs.
                Nodes with dashed lines are disabled jobs.
                The last build number for each job is shown as #<number>.
                The runtime of the last build is shown as (<time>).
                If the last build failed, then we would mark the job's text as red.
        """

        log.info("Generating job dependency graph...")

        if not graph_path:
            log.error("graph_path is not specified")
            return

        # do not print deprecation warning
        # about 'nx.nx_pydot.graphviz_layout'
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        jobs_no_dependency = []

        g = nx.DiGraph()

        root_id = "#"
        g.add_node(root_id, label="root")

        # get information about all jobs
        jobs_dict_ = self.get_all_jobs_detail(include_build=False)

        for job_name in jobs_dict_:
            g.add_node(job_name, label=job_name)

        for job_name, job_params in jobs_dict_.items():

            upstream_proj = job_params.get("upstreamProjects", None)
            downstream_proj = job_params.get("downstreamProjects", None)

            # remove standalone jobs from the graph
            if not upstream_proj and not downstream_proj:
                g.remove_node(job_name)
                jobs_no_dependency.append(job_name)
                continue

            if upstream_proj:
                for p in upstream_proj:
                    g.add_edge(p, job_name)
            else:
                g.add_edge(root_id, job_name)

            if downstream_proj:
                for p in downstream_proj:
                    g.add_edge(job_name, p)

        # from networkx.drawing.nx_agraph import graphviz_layout
        # import matplotlib.pyplot as plt

        # img_file_n = os.path.join(script_dir, "jobs_tree_nx.png")
        # #nx.draw(g, with_labels=True, pos=nx.nx_pydot.graphviz_layout(g, prog="dot"))
        # nx.draw(g, with_labels=True, pos=nx.nx_pydot.graphviz_layout(g, prog="circo"))
        # plt.savefig(img_file_n)

        if jobs_no_dependency:
            log.info("\nThese jobs have no upstream and downstream:")
            for j in jobs_no_dependency:
                log.info(" "*4 + j)

        log.info("\nGenerating graph...")
        pdot = nx.drawing.nx_pydot.to_pydot(g)

        pdot_nodes = pdot.get_nodes()

        # https://github.com/pydot/pydot/issues/169

        for node in pdot_nodes:

            node.set_shape('ellipse')

            job_name = node.get_label()

            if job_name == "root":
                node.set_shape('triangle')
                node.set_style('bold')

            job_params = jobs_dict_.get(job_name, None)

            if job_params:

                view_list = job_params.get("view", None)
                if view_list and "Nightlies" in view_list:
                    node.set_color('green')

                disabled = job_params.get("disabled", None)
                if disabled:
                    node.set_style('dashed')

                lastBuildNumber = job_params.get("lastBuild", None)

                if lastBuildNumber:

                    node_l = f" {job_name} #{lastBuildNumber}"
                    node.set_label(node_l)

                    build_info = self.server.get_build_info(job_name, lastBuildNumber)

                    duration = build_info.get("duration", None)
                    if duration:
                        duration_str = Utility_Time.elapsed_format(duration/100, short=True)
                        node_l += f" ({duration_str})"
                        node.set_label(node_l)

                    result = build_info.get("result", None)
                    if result and result != "SUCCESS":
                        node.set_fontcolor('red')

        log.info("\nSaving job dependency graph into: %s", graph_path)
        pdot.write_png(graph_path)


    def disable_jobs(self, jobs_to_disable):

        jobs_to_disable_list = jobs_to_disable.split(",")

        for j in jobs_to_disable_list:
            log.info("disabling job '%s'", j)
            try:
                self.server.disable_job(j)
            except Exception as E:
                log.error(E)


    def enable_jobs(self, jobs_to_enable):

        jobs_to_enable_list = jobs_to_enable.split(",")

        for j in jobs_to_enable_list:
            log.info("enabling job '%s'", j)
            try:
                self.server.enable_job(j)
            except Exception as E:
                log.error(E)


    def delete_jobs(self, jobs_to_delete):

        log.warning("Not implemented for security reasons!")


    def launch_build(self, job_name, build_params_file=None, build_params=None):
        """
            job_name=<job-name> --> launch a build with no parameters

            job_name=<job-name> build_params_file=<contains a dictionary of key-value pairs>:

            {
                'param1': 'test value 1',
                'param2': 'test value 2'
            }
        """

        try:
            job_info = self.server.get_job_info(job_name)
        except Exception as E:
            return False, f"cannot get job information: {E}"

        next_build_number = job_info.get('nextBuildNumber', None)
        if not next_build_number:
            return False, f"cannot get next build number for job '{job_name}'"

        if build_params_file:

            if not os.path.exists(build_params_file):
                return False, f"cannot access build parameter file at '{build_params_file}'"

            with open(build_params_file, 'r') as fin:
                params_str = fin.read()
                params_str = params_str.strip()

            try:
                parameters = ast.literal_eval(params_str)
            except Exception as E:
                return False, "build_params_file is malformed"

            if not isinstance(parameters, dict):
                return False, "build_params_file should contain a dictionary"

        elif build_params:

            build_params = textwrap.dedent(build_params)
            build_params = build_params.strip()

            try:
                parameters = ast.literal_eval(build_params)
            except Exception as E:
                return False, f"build_params_file is malformed: {E}"

            if not isinstance(parameters, dict):
                return False, "build_params_file should contain a dictionary"

        else:

            parameters = None

        ###

        log.info("Starting build '%s' for job '%s'", next_build_number, job_name)

        try:
            self.server.build_job(job_name,
                                  parameters=parameters)
        except Exception as E:
            return False, f"build job error: {E}"

        ###

        log.info("Waiting for 10 seconds...")
        time.sleep(10)

        max_try = 50   # maximum try count
        try_wait = 10  # wait between each try
        try_count = 1

        while True:

            log.info("Getting the new build information (try %s/%s)", try_count, max_try)

            try:
                build_info_ = self.server.get_build_info(job_name,
                                                         next_build_number)
                return True, build_info_
            except Exception as E:
                log.error(E)

                if try_count >= max_try:
                    return False, "max_try reached. Bailing out."

            try_count += 1
            time.sleep(try_wait)


    def stop_build(self, job_name, build_to_stop):

        build_to_stop_list = build_to_stop.split(",")

        for number in build_to_stop_list:
            log.info("stopping build '%s' in job '%s'", number, job_name)
            self.server.stop_build(job_name, number)


    def get_nodes(self):

        nodes = self.server.get_nodes()

        node_dict = {}

        for node in nodes:
            name = node.get("name", None)
            node_dict[name] = self.server.get_node_info(name)

        return node_dict
