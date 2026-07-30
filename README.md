
Gcloud Steps : 
- Revoke everything before starting
  - gcloud auth revoke --all
- Connect to gcloud via cli
  - gcloud auth login
- If a project is set and you want to remove it
  - gcloud config unset project
- Set up application default credentials
  - gcloud auth application-default login


Terraform Steps On Mac/Ubuntu:
- Install Hashicorp Tap :
  - brew tap hashicorp/tap
  - sudo snap install terraform --classic
- Install Terraform
  - brew install hashicorp/tap/terraform
- Test it out
  - terraform -help
- For autocomplete package
  - terraform -install-autocomplete
- Initialize working directory
  - terraform init
- Working with Terraform
  - terraform fmt : For formatting
  - terraform plan : For planning changes
  - terraform apply : For applying changes (asks for confirmation)
  - terraform apply -auto-approve : For applying changes automatically without confirmation

Kubernetes Steps On Mac :
- Install GKE CLOUD AUTHENTICATION PLUGIN for Kubernetes
  - gcloud components install gke-gcloud-auth-plugin
- Get credentials for your local machine :
  - gcloud container clusters get-credentials "CLUSTER_NAME" --zone "ZONE" --project "PROJECT_NAME"
In our case """gcloud container clusters get-credentials machine-learning-cluster --zone europe-west4-b  --project ml-ops-classifier-app"""
- In order to verify that you have access to the nodes
  - kubectl get nodes
You should see something like this :
'''
# In our case we had 2 nodes
gke-machine-learning-machine-learning-82e85027-128t   Ready    <none>   3h47m   v1.35.6-gke.1049000
gke-machine-learning-machine-learning-82e85027-t93d   Ready    <none>   3h47m   v1.35.6-gke.1049000
'''
- Download the official NVIDIA DaemonSet for GPU drivers (run inside the kubernetes folder):
  - curl -o nvidia-daemonset.yaml https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded-latest.yaml
- Deploy the gradio app using kubernetes it will get the docker image, and create as much containers as specified by our gradio.yaml file.
  - kubectl apply -f gradio.yaml
- To watch the pods start
  - kubectl get pods -l app=gradio --watch
- To get the ip for the specific load balancer
  - kubectl get service gradio-service --watch



- Configure connection to Artifact Registry
  - gcloud auth configure-docker "LOCATION"-docker.pkg.dev
In our case : "gcloud auth configure-docker europe-west4-docker.pkg.dev"


Docker Building :
- docker cross platform build (since we are on an arm based linux architecture)
  - docker buildx create --name cross-compiler --use
  - docker buildx inspect --bootstrap
- Build and send it to the artifact registry
  - docker buildx build --platform linux/amd64 --load -t europe-west4-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v2 .
- Push to the artifacts registry
  - Might need to reauthenticate : "gcloud auth configure-docker europe-west4-docker.pkg.dev"
  - docker push europe-west4-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v2
- gcloud artifacts docker images list europe-west4-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry


# Uploading Models To Google Cloud
- Uploading models to google cloud
  - gcloud storage cp -r served_models/ gs://machine-learning-ops-images-bucket-2026/



Next Steps :

- Make Gradio App
- Make Dockerfile for the App
- Create Google Cloud Infrastructure Via Terraform
  - Virtual Machines x2
  - VPC Network
  - Kubernetes
    - Should have load balancer
    - 2 Triton Servers
    - 4 Gradio Applications
      - Add environment variables identifying each machine/pod to make sur everything is ok
  - Google Cloud Storage For Saving Images
  - BigQuery Database For Storing Predictions
  - Set Up Of Secret Managers
  - Set Up Of Artifacts Registry
  - Set Up Of VPC For Communication

# Important todos to be tackled later
- Move the terraform state file to google cloud storage

# Troubleshooting

### Debugging Stuck Node Provisioning
If `terraform apply` hangs while creating node pools (often caused by GPU stockouts or quota limits), you can use the `gcloud` CLI to check the status directly on Google Cloud:

**1. Check if the cluster is stuck in a `RECONCILING` state:**
```bash
gcloud container clusters list
```
*Example Output (Notice the STATUS column):*
```text
NAME                      LOCATION        NUM_NODES  STATUS
machine-learning-cluster  europe-west4-b  2          RECONCILING
```

**2. List all node pools to see which ones exist:**
```bash
gcloud container node-pools list --cluster machine-learning-cluster --location europe-west4-b
```
*Example Output:*
```text
NAME                               MACHINE_TYPE   DISK_SIZE_GB
gradio-machine-learning-node-pool  e2-standard-4  50
triton-machine-learning-node-pool  n1-standard-4  50
```

**3. Get detailed error messages for a specific stuck node pool:**
By describing the specific node pool, you can often find a `statusMessage` at the bottom of the output explaining *why* it is stuck (e.g., "Insufficient regional quota").
```bash
gcloud container node-pools describe triton-machine-learning-node-pool --cluster machine-learning-cluster --location europe-west4-b
```

**4. Delete a stuck node pool to unblock Terraform:**
If a node pool is hopelessly stuck (for example, due to a GPU stockout error in GCP) and it's preventing `terraform plan` or `terraform apply` from running because Terraform tries to "resume" it, you can forcefully delete it using `gcloud`. Once deleted from GCP, Terraform will cleanly recreate it without errors.
```bash
gcloud container node-pools delete triton-machine-learning-node-pool --cluster machine-learning-cluster --zone europe-west4-b --quiet
```