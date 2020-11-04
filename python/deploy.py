from kube_deployer import read_conf, ClusterDeployer, ClusterPreparer
from threading import Thread
import time
import sys
#from MasterNode import MasterNode
#from WorkerNode import WorkerNode

def prepare(conf_dir='config'):
    print('### Preparing Kubernetes Cluster Nodes ###')
    cluster_conf = read_conf('{}/cluster.yaml'.format(conf_dir))
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

def deploy(conf_dir='config'):
    cluster_conf = read_conf('{}/cluster.yaml'.format(conf_dir))
    plugin_conf = read_conf('{}/plugins.yaml'.format(conf_dir))
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
    # Budget version of the Argument selector that needs to be implemented
    try: # If user selects a specific option and cluster
        command, cluster = sys.argv[1].split('=')
        cluster_conf = 'config/clusters/{}'.format(cluster)
        if command == 'prepare':
            prepare(conf_dir=cluster_conf)
        if command == 'deploy':
            deploy(conf_dir=cluster_conf)
    except:
        print('For now - We break...')
        exit()
    #prepare()
    #deploy()