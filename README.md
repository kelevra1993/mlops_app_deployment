# MLOps Application Deployment Pipeline

Welcome to the MLOps Application Deployment repository! This project provisions a fully functional Machine Learning pipeline on Google Cloud Platform (GCP). It uses **Terraform** for infrastructure, **Google Kubernetes Engine (GKE)** for orchestration, a **Gradio** frontend for the user interface, and an **NVIDIA Triton Inference Server** backend (equipped with GPU acceleration) for high-performance model serving.

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
Configure Docker to authenticate with GCP:
```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

### Uploading Models to GCS
Triton expects your ML models to be available in a Google Cloud Storage bucket.
```bash
gcloud storage cp -r served_models/ gs://machine-learning-ops-images-bucket-2026/
```

### Kubernetes Cluster Access
Install the GKE Auth Plugin and connect to your new cluster:
```bash
gcloud components install gke-gcloud-auth-plugin
gcloud container clusters get-credentials machine-learning-cluster --zone europe-west1-b --project ml-ops-classifier-app
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
gcloud container node-pools list --cluster machine-learning-cluster --location europe-west1-b
```

**3. Read the error message:**
```bash
gcloud container node-pools describe triton-machine-learning-node-pool --cluster machine-learning-cluster --location europe-west1-b
```

**4. Delete the stuck node pool manually to unblock Terraform:**
```bash
gcloud container node-pools delete triton-machine-learning-node-pool --cluster machine-learning-cluster --zone europe-west1-b --quiet
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
# Initialize Terraform providers
terraform init

# Review the planned changes
terraform plan

# Apply the changes to Google Cloud
terraform apply -auto-approve
```
*(Tip: `terraform fmt` can be used to automatically format your configuration files).*

---

## 3. Docker (docker)

We need to build our Gradio application into a Docker container and push it to the Google Artifact Registry created by Terraform.

**1. Build the Docker Image (Cross-platform for ARM/Mac users):**
```bash
# Setup cross-compiler
docker buildx create --name cross-compiler --use
docker buildx inspect --bootstrap

# Build and load the image locally
docker buildx build --platform linux/amd64 --load -t europe-west1-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v2 .
```

**2. Push the image to Artifact Registry:**
```bash
docker push europe-west1-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v2
```

---

## 4. Kubernetes (kubectl)

Once the infrastructure is up, images are pushed, and models are uploaded, we deploy the workloads to GKE.

**1. Verify node access:**
```bash
kubectl get nodes
```

**2. Install NVIDIA GPU Drivers (DaemonSet):**
*Must be run to allow Triton to utilize the GPUs.*
```bash
curl -o nvidia-daemonset.yaml https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded-latest.yaml
kubectl apply -f nvidia-daemonset.yaml
```

**3. Deploy Applications:**
```bash
# Deploy Triton and Gradio
kubectl apply -f kubernetes/applications/triton.yaml
kubectl apply -f kubernetes/applications/gradio.yaml

# Watch pods start
kubectl get pods -l app=gradio --watch

# Get the public IP of the Gradio LoadBalancer
kubectl get service gradio-service --watch
```

---

## 5. Next Steps & Roadmap

- [x] Verified Git Autonomy.
- **Move the Terraform state file** to a Google Cloud Storage backend for shared state management.
- Ensure environment variables identifying each machine/pod are injected properly.
- Finalize Secrets Manager integration.
- Ensure seamless VPC communication between all components.

---
*Note: This infrastructure setup is highly autonomous. Terraform may destroy and recreate resources (like Node Pools) automatically to bypass cloud capacity limits.*