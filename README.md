# deploy-binderhub
Automated Deployment for BinderHub

# How To
- Run from root dir.
- Add directory to 'config/clusters' with your clusters_name.
- Copy example 'cluster.yaml' and 'plugin.yaml' from 'config/examples' into your new directory.
- Edit Example 'cluster.yaml' and 'plugin.yaml' to your liking.
- Run 'python|3 prepare=cluster_name to install Docker and Kubernetes on nodes.
- Run 'python|3 deploy=cluster_name to initialize your Kubernetes cluster and install plugins.
