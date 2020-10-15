#!usr/bin/python3
import subprocess
from fabric import Connection, ThreadingGroup, SerialGroup
import getpass
import json


def get_node_list(node_config):
    return node_config["workers"] + [node_config["master"]]

def get_node_group(nodes):
    return ThreadingGroup(*nodes, user="root", forward_agent=True)

def node_group_put(node_group, local_path, remote_path):
    for conn in node_group:
        conn.put(local_path, remote=remote_path)


### ALL NODES CODE ###
def prepare_kubeadm(config):
    # Get all the nodes
    nodes = get_node_list(config["nodes"])
    node_group = get_node_group(nodes)
    node_group.run("echo this works")

    # Configure IP Tables
    node_group_put(node_group, "kube_files/k8s.conf", "/etc/sysctl.d/k8s.conf")
    node_group.run("sysctl --system")

    # Install Required Everything (APT, Docker, Kube)
    install_packages(config["base_packages"], node_group)
    install_docker(config["docker_packages"], node_group)
    install_kubeadm(config["kube_packages"], node_group)


def install_packages(package_list, node_group):
    node_group.run("apt-get update")
    node_group.run("apt-get install -y {}".format(" ".join(package_list)))

def install_docker(docker_packages, node_group):
    node_group.run("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -")
    node_group.run('sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"')
    install_packages(docker_packages, node_group)
    node_group_put(node_group, "kube_files/daemon.json", "/etc/docker/daemon.json")
    node_group.run("mkdir -p /etc/systemd/system/docker.service.d")
    node_group.run("sudo systemctl daemon-reload")
    node_group.run("sudo systemctl restart docker")
    node_group.run("sudo systemctl enable docker")

def install_kubeadm(kube_packages, node_group):
    node_group.run("curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -")
    node_group_put(node_group, "kube_files/kubernetes.list", "/etc/apt/sources.list.d/kubernetes.list")
    install_packages(kube_packages, node_group)
    node_group.run("apt-mark hold {}".format(" ".join(kube_packages)))


def read_cluster_conf():
    with open("cluster/cluster.json", "r") as f:
        config = json.load(f)
    return config

if __name__ == "__main__":
    config = read_cluster_conf()
    prepare_kubeadm(config)