#!usr/bin/python3
import subprocess
from fabric import Connection, ThreadingGroup, SerialGroup
import getpass
import json
import time
import yaml
import sys #just for refractoring


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
    node_group.run("Hi - You have connected to a node.")

    # Disable Swap
    node_group.run("swapoff -a; sed -i '/swap/d' /etc/fstab")

    # Configure IP Tables
    node_group_put(node_group, "kube_files/nodes/k8s.conf", "/etc/sysctl.d/k8s.conf")
    node_group.run("sysctl --system")

    # Install Required Everything (APT, Docker, Kube)
    install_packages(config["base_packages"], node_group)
    install_docker(config["docker_packages"], node_group)
    install_kubeadm(config["kube_packages"], node_group)


def install_packages(package_list, node_group, mark=False):
    node_group.run("apt-get update")
    node_group.run("apt-get install -y {}".format(" ".join(package_list)))
    if mark:
        node_group.run("apt-mark hold {}".format(" ".join(package_list)))

def install_docker(docker_packages, node_group):
    node_group.run("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -")
    node_group.run('sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"')
    install_packages(docker_packages, node_group)
    node_group_put(node_group, "kube_files/nodes/daemon.json", "/etc/docker/daemon.json")
    node_group.run("mkdir -p /etc/systemd/system/docker.service.d")
    node_group.run("sudo systemctl daemon-reload")
    node_group.run("sudo systemctl restart docker")
    node_group.run("sudo systemctl enable docker")

def install_kubeadm(kube_packages, node_group):
    node_group.run("curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -")
    node_group_put(node_group, "kube_files/nodes/kubernetes.list", "/etc/apt/sources.list.d/kubernetes.list")
    install_packages(kube_packages, node_group)
    node_group.run("apt-mark hold {}".format(" ".join(kube_packages)))

def init_kubeadm(config):
    # Get Connections
    init_conf = config["init"]
    master_conn = Connection(config["nodes"]["master"], user="root")
    worker_group = ThreadingGroup(*config["nodes"]["workers"], user="root")

    # Run Init and Join Nodes
    master_conn.run("kubeadm init --apiserver-advertise-address={} --pod-network-cidr={}".format(init_conf["api_server"], init_conf["pod_network"]))
    master_conn.run("mkdir -p $HOME/.kube")
    master_conn.run("cp -i /etc/kubernetes/admin.conf $HOME/.kube/config")
    master_conn.run("chown $(id -u):$(id -g) $HOME/.kube/config")
    join_cmd = master_conn.run("kubeadm token create --print-join-command", hide=True).stdout
    worker_group.run(join_cmd)
    print("Waiting for Nodes to Join")
    time.sleep(30)

def install_plugins(config):
    plugin_conf = config["plugins"]
    master_conn = Connection(config["nodes"]["master"], user="root")
    install_calico(master_conn, plugin_conf['calico'])
    install_helm(master_conn, plugin_conf['helm'])
    install_metallb(master_conn, plugin_conf['metallb'])
    install_nfs_client_provisioner(master_conn, plugin_conf['nfs-client-provisioner'])
    
def install_calico(master_conn, calico_conf):
    master_conn.run("kubectl create -f https://docs.projectcalico.org/manifests/tigera-operator.yaml")
    master_conn.run("kubectl create -f https://docs.projectcalico.org/manifests/custom-resources.yaml")
    master_conn.run("kubectl apply -f https://docs.projectcalico.org/manifests/calicoctl.yaml")
    master_conn.run('alias calicoctl="kubectl exec -i -n kube-system calicoctl -- /calicoctl"')
    print("Waiting for Calico to Initialize")
    time.sleep(30)

def install_helm(master_conn, helm_conf):
    if helm_conf["version"] == "2":
        master_conn.run("curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get | bash")
    elif helm_conf["version"] == "3":
        master_conn.run('curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash')
    else:
        print("No Helm Version Specified - Exiting")
        exit()
    master_conn.run("kubectl --namespace kube-system create serviceaccount tiller")
    master_conn.run("kubectl create clusterrolebinding tiller --clusterrole cluster-admin --serviceaccount=kube-system:tiller")
    master_conn.run("helm init --service-account tiller --history-max 100 --wait")
    master_conn.run('kubectl patch deployment tiller-deploy --namespace=kube-system --type=json --patch=\'[{"op": "add", "path": "/spec/template/spec/containers/0/command", "value": ["/tiller", "--listen=localhost:44134"]}]\'')
    print("Waiting for Helm and Tiller to Initialize")
    time.sleep(30)

def install_metallb(master_conn, metallb_conf):
    # Just Reading Config for now, Reading from Clusters
    master_conn.run("kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.9.3/manifests/namespace.yaml")
    master_conn.run("kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.9.3/manifests/metallb.yaml")
    master_conn.run('kubectl create secret generic -n metallb-system memberlist --from-literal=secretkey="$(openssl rand -base64 128)"')
    master_conn.run('mkdir -p /root/kube_plugins/metallb')
    master_conn.put('kube_files/plugins/metallb/config.yaml', remote="/root/kube_plugins/metallb/config.yaml")
    master_conn.run('kubectl apply -f /root/kube_plugins/metallb/config.yaml')
    print("Waiting for MetalLB to Initialize")
    time.sleep(30)

def install_nfs_client_provisioner(master_conn, nfs_client_conf):
    nfs_ns = nfs_client_conf["namespace"]
    nfs_server = nfs_client_conf["nfs_server"]
    nfs_path = nfs_client_conf["nfs_path"]
    master_conn.run("helm install --namespace {} --set nfs.server={} --set nfs.path={} stable/nfs-client-provisioner".format(nfs_ns, nfs_server, nfs_path))

def install_binderhub(config):
    # When trying to automate - need to work on editing YAML file on the side...

    # Setup Config Files
    master_conn = Connection(config["nodes"]["master"], user="root")
    remote_dir = "/root/kube_plugins/binderhub/"
    remote_config = remote_dir + "config.yaml"
    remote_secret = remote_dir + "secret.yaml"

    master_conn.run('mkdir -p /root/kube_plugins/binderhub')
    master_conn.put('kube_files/plugins/binderhub/config.yaml', remote=remote_config)
    master_conn.put('kube_files/plugins/binderhub/secret.yaml', remote=remote_secret)

    # Should move these to package vars
    version = "0.2.0-n224.hf5cc56a"
    name = "binder"
    namespace = "binder"
    config_flags = '-f {} -f {}'.format(remote_secret, remote_config) # To shorten the log lings a bit (it is passed to helm)
    
    # Setup Binderhub Chart
    master_conn.run('helm repo add jupyterhub https://jupyterhub.github.io/helm-chart')
    master_conn.run('helm repo update')
    master_conn.run('helm install jupyterhub/binderhub --version={} --name={} --namespace={} {}'.format(version, name, namespace, config_flags))

    # Find External IP
    svc = master_conn.run('kubectl --namespace={} get svc proxy-public'.format(namespace)).stdout
    external_ip = svc.split("\n")[1].split()[3]
    binder_conf = read_yaml_conf('kube_files/plugins/binderhub/config.yaml')
    binder_conf['config']['BinderHub']['hub_url'] = "http://{}".format(external_ip)
    write_yaml_conf(binder_conf, 'kube_files/plugins/binderhub/update_config.yaml')
    master_conn.put('kube_files/plugins/binderhub/update_config.yaml', remote=remote_config)
    master_conn.run('helm upgrade {} jupyterhub/binderhub --version={} {}'.format(name, version, config_flags))


def write_yaml_conf(data, conf_file):
    with open(conf_file, 'w') as f:
        yaml.dump(data, f)

def read_yaml_conf(conf_file):
    with open(conf_file) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data

def read_cluster_conf():
    with open("cluster/cluster.json", "r") as f:
        config = json.load(f)
    return config

if __name__ == "__main__":
    config = read_cluster_conf()
    print("Making this more modular - then moving to classes.")
    try:
        if sys.argv[1] == "prepare":
            print("Preparing Cluster Nodes")
            prepare_kubeadm(config)
        if sys.argv[1] == "init":
            print("Initialiing Kube Cluster")
            init_kubeadm(config)
        if sys.argv[1] == "plugins":
            print("Installing Plugins")
            install_plugins(config)
        if sys.argv[1] == "binderhub":
            print("Installing Binderhub")
            install_binderhub(config)
    except:
        print("This is still in alpha, please follow the rules")
        exit()