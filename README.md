# MLOps Application Deployment Pipeline

This project provisions a Machine Learning pipeline on Google Cloud Platform (GCP) using Terraform, Google Kubernetes Engine (GKE), Gradio, and NVIDIA Triton Inference Server.

---

## Table of Contents
1. [Google Cloud SDK (gcloud)](#1-google-cloud-sdk-gcloud)
2. [Terraform (terraform)](#2-terraform-terraform)
3. [Docker (docker)](#3-docker-docker)
4. [Kubernetes (kubectl)](#4-kubernetes-kubectl)
5. [Next Steps & Roadmap](#5-next-steps--roadmap)

---

## 1. Google Cloud SDK (gcloud)

### Prerequisites & Authentication
Before starting, you must authenticate your local machine with Google Cloud.

**1. Revoke existing credentials (optional, for a clean slate):**
```bash
gcloud auth revoke --all
gcloud config unset project
```

**2. Login to Google Cloud:**
```bash
gcloud auth login
```

**3. Set Application Default Credentials (used by Terraform):**
```bash
gcloud auth application-default login
```

### Docker Authentication
Configure Docker to authenticate with GCP's Artifact Registry, allowing you to push and pull images securely:
```bash
gcloud auth configure-docker europe-west3-docker.pkg.dev
```

### Uploading Models to GCS
Triton expects your ML models to be available in a Google Cloud Storage bucket so it can serve them efficiently on the backend. Since the provided models are stored locally within the `docker/triton/served_models` directory, you need to upload them to the GCS bucket created by Terraform.
```bash
gcloud storage cp -r docker/triton/served_models/ gs://machine-learning-ops-images-bucket-2026/
```

### Kubernetes Cluster Access
Install the GKE Auth Plugin and fetch the cluster credentials so your local `kubectl` tool can communicate directly with your newly created Kubernetes API server:
```bash
gcloud components install gke-gcloud-auth-plugin
gcloud container clusters get-credentials machine-learning-cluster --zone europe-west3-a --project ml-ops-classifier-app
```

### Troubleshooting Stuck Node Provisioning
If Terraform hangs while creating node pools, you can use `gcloud` to troubleshoot:

**1. Check cluster status:**
```bash
gcloud container clusters list
```
*(If the status is `RECONCILING`, GKE is currently locked updating a node pool).*

**2. View existing node pools:**
```bash
gcloud container node-pools list --cluster machine-learning-cluster --location europe-west3-a
```

**3. Read the error message:**
```bash
gcloud container node-pools describe triton-machine-learning-node-pool --cluster machine-learning-cluster --location europe-west3-a
```

**4. Delete the stuck node pool manually to unblock Terraform:**
```bash
gcloud container node-pools delete triton-machine-learning-node-pool --cluster machine-learning-cluster --zone europe-west3-a --quiet
```

---

## 2. Terraform (terraform)

We use Terraform to automatically spin up the VPC, Kubernetes Cluster, Node Pools, Artifact Registry, Storage Buckets, and BigQuery datasets.

**1. Install Terraform (Mac/Ubuntu):**
```bash
# Mac using Homebrew
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Ubuntu using Snap
sudo snap install terraform --classic
```

**2. Deploy the Infrastructure:**
```bash
# Initialize Terraform providers (downloads the required plugins to communicate with GCP)
terraform init

# Review the planned changes (shows a dry-run of what infrastructure will be created/destroyed)
terraform plan

# Apply the changes to Google Cloud (provisions the actual cloud infrastructure based on the plan)
terraform apply -auto-approve
```
*(Tip: `terraform fmt` can be used to automatically format your configuration files).*

---

## 3. Docker (docker)

We need to build our Gradio application into a Docker container and push it to the Google Artifact Registry created by Terraform.

**1. Setup Cross-Compiler (For ARM/Mac users):**
*Ensures the Docker image is built for the standard linux/amd64 architecture expected by GKE, regardless of your local machine.*
```bash
docker buildx create --name cross-compiler --use
docker buildx inspect --bootstrap
```

**2. Build and Push the Docker Image:**
*Builds the image from the local `app` directory and pushes it directly to the Artifact Registry in one step.*
```bash
docker buildx build --platform linux/amd64 -t europe-west3-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v3 --push ./app
```

---

## 4. Kubernetes (kubectl)

Once the infrastructure is up, images are pushed, and models are uploaded, we deploy the workloads to GKE.

**1. Verify node access:**
```bash
kubectl get nodes
```

**2. Install NVIDIA GPU Drivers (DaemonSet):**
*Deploys a DaemonSet (a pod on every eligible node) that automatically installs the proprietary NVIDIA GPU drivers onto your GKE nodes. This is mandatory for Triton to utilize the attached L4 GPUs.*
```bash
curl -o nvidia-daemonset.yaml https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded-latest.yaml
kubectl apply -f nvidia-daemonset.yaml
```

**3. Deploy Applications:**
*Applies the Kubernetes manifests to create the Deployments (Pods) and Services (Networking).*
```bash
# Deploy Triton Backend and Gradio Frontend
kubectl apply -f kubernetes/applications/triton.yaml
kubectl apply -f kubernetes/applications/gradio.yaml

# Watch the Gradio pods as they transition from 'Pending' to 'Running'
kubectl get pods -l app=gradio --watch

# Wait for GCP to provision an external IP for the Gradio Service LoadBalancer
kubectl get service gradio-service --watch
```

**4. Access the Live Application:**
Once the LoadBalancer is fully provisioned, the Gradio frontend is available to the public. 
The application is currently live and accessible at: 
**http://34.107.100.71:80**


---

## 5. Next Steps & Roadmap
 
 - Ensure environment variables identifying each machine/pod are injected properly.
 - Finalize Secrets Manager integration.
 - Ensure seamless VPC communication between all components.
 
 ---
 
 ## 6. Terraform State Management
 
 We have migrated the local Terraform state to a Google Cloud Storage (GCS) backend for secure, shared state management. This ensures that the state is not lost and allows for collaboration without state conflicts.
 
 **Bucket Name**: `gs://ml-ops-infrastructure-2026`
 
 **Migration Command Used**:
 ```bash
 terraform init -migrate-state
 ```

---
*Note: This infrastructure setup is highly autonomous. Terraform may destroy and recreate resources (like Node Pools) automatically to bypass cloud capacity limits.*

---

## 6. Debugging History & Corrections

During the initial deployment of the Kubernetes cluster, a few misconfigurations were successfully debugged and corrected:

1. **Node Pool Name Mismatch (`kubernetes/applications/triton.yaml`)**:
   - *Bug*: Triton pods were stuck in the `Pending` state.
   - *Debugging*: We inspected the Terraform configuration and discovered the actual provisioned name for the GPU Node Pool was `triton-reserved-node-pool`. The `triton.yaml` file was incorrectly attempting to schedule pods onto a non-existent `triton-machine-learning-node-pool`.
   - *Fix*: Updated the `nodeSelector` in `triton.yaml` to exactly match the Terraform node pool name.

2. **Gradio Node Selector Absent (`kubernetes/applications/gradio.yaml`)**:
   - *Bug*: Gradio pods could randomly be scheduled onto expensive L4 GPU nodes since they lacked any `nodeSelector`.
   - *Fix*: Added a `nodeSelector` specifically targeting the standard compute `gradio-machine-learning-node-pool` to strictly isolate workload costs.

3. **GCS Bucket IAM Permissions (`terraform/main.tf`)**:
   - *Bug*: Once Triton was scheduled, the pod continuously crashed with `Permission 'storage.buckets.get' denied`.
   - *Debugging*: We inspected the Triton Pod logs using `kubectl logs` and identified the container could not fetch the model repository bucket metadata. The Service Account bound to the Kubernetes node pool was originally only granted `roles/storage.objectAdmin`, which allows managing objects inside buckets, but does NOT grant permission to read the bucket's overarching metadata.
   - *Fix*: Upgraded the Terraform IAM binding for the node service account to `roles/storage.admin`, granting full access to GCS. Re-applied Terraform, waited for IAM propagation, and restarted the pod.

4. **Kubernetes API `i/o timeout` (Local Machine Sync)**:
   - *Bug*: When running `kubectl apply`, the terminal threw an `i/o timeout` connecting to the Kubernetes control plane IP.
   - *Debugging*: We realized the infrastructure was spun up on a different machine (or CI/CD runner). Running `terraform plan` locally showed `24 to add`, meaning the local Terraform state was empty and unaware of the active cluster.
   - *Fix*: We determined that running `terraform apply` locally would mistakenly attempt to recreate the infrastructure. Instead, we simply synced the local machine to the existing cluster by fetching the credentials via `gcloud container clusters get-credentials <CLUSTER_NAME> --region <REGION> --project <PROJECT_ID>`.

Next things that will need to be implemented :

Refactoring of the whole repository :
- Utilities folder will contain different sorts of utility functions separated clearly
  - os_utilities
  - google_cloud_utilities
    - merging gcs and bigquery
- Inference data to be renamed to data.
