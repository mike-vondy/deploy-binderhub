from helpers import get_node, get_node_group, read_conf
from ClusterPreparer import ClusterPreparer
from ClusterDeployer import ClusterDeployer
from threading import Thread
import time
#from MasterNode import MasterNode
#from WorkerNode import WorkerNode

def prepare():
    print('### Preparing Kubernetes Cluster Nodes ###')
    cluster_conf = read_conf('config/cluster/nodes.yaml')
    with ClusterPreparer(cluster_conf) as preparer:
        status_watcher = Thread(target=preparer.prepare)
        status_watcher.start()
        current_status = preparer.status
        while True:
            if current_status != preparer.status:
                print(preparer)
            current_status = preparer.status
            if current_status == 'Complete' or current_status == 'Exiting':
                print('--- Cluster Preperation Complete ---')
                break

def deploy():
    cluster_conf = read_conf('config/cluster.yaml')
    plugin_conf = read_conf('config/plugins.yaml')
    print('### Deploying Kubernetes and Plugins ###')
    with ClusterDeployer(cluster_conf, plugin_conf) as deployer:
        status_watcher = Thread(target=deployer.deploy)
        status_watcher.start()
        current_status = deployer.status
        while True:
            if current_status != deployer.status:
                print(deployer)
            current_status = deployer.status
            if current_status == 'Cluster Deployment - Complete' or current_status == 'Cluster Deployment - Failed':
                print('--- Cluster Deployment Exiting ---')
                break

if __name__=="__main__":
    prepare()
    deploy()