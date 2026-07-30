# MLOps Application Deployment Pipeline

Welcome to the MLOps Application Deployment repository! This project provisions a fully functional Machine Learning pipeline on Google Cloud Platform (GCP). It uses **Terraform** for infrastructure, **Google Kubernetes Engine (GKE)** for orchestration, a **Gradio** frontend for the user interface, and an **NVIDIA Triton Inference Server** backend (equipped with GPU acceleration) for high-performance model serving.

---

## Table of Contents
1. [Prerequisites & Authentication](#1-prerequisites--authentication)
2. [Infrastructure Provisioning (Terraform)](#2-infrastructure-provisioning-terraform)
3. [Docker Build & Push](#3-docker-build--push)
4. [Uploading Models to GCS](#4-uploading-models-to-gcs)
5. [Kubernetes Deployment](#5-kubernetes-deployment)
6. [Troubleshooting](#6-troubleshooting)
7. [Next Steps & Roadmap](#7-next-steps--roadmap)

---

## 1. Prerequisites & Authentication
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

---

## 2. Infrastructure Provisioning (Terraform)
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

## 3. Docker Build & Push
We need to build our Gradio application into a Docker container and push it to the Google Artifact Registry created by Terraform.

**1. Configure Docker to authenticate with GCP:**
```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

**2. Build the Docker Image (Cross-platform for ARM/Mac users):**
```bash
# Setup cross-compiler
docker buildx create --name cross-compiler --use
docker buildx inspect --bootstrap

# Build and load the image locally
docker buildx build --platform linux/amd64 --load -t europe-west1-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v2 .
```

**3. Push the image to Artifact Registry:**
```bash
docker push europe-west1-docker.pkg.dev/ml-ops-classifier-app/machine-learning-artifacts-registry/gradio-app:v2
```

---

## 4. Uploading Models to GCS
Triton expects your ML models to be available in a Google Cloud Storage bucket.

```bash
gcloud storage cp -r served_models/ gs://machine-learning-ops-images-bucket-2026/
```

---

## 5. Kubernetes Deployment
Once the infrastructure is up and the images/models are uploaded, we deploy the workloads to GKE.

**1. Install the GKE Auth Plugin:**
```bash
gcloud components install gke-gcloud-auth-plugin
```

**2. Connect `kubectl` to your new cluster:**
```bash
gcloud container clusters get-credentials machine-learning-cluster --zone europe-west1-b --project ml-ops-classifier-app
```

**3. Verify node access:**
```bash
kubectl get nodes
```

**4. Install NVIDIA GPU Drivers (DaemonSet):**
*Must be run to allow Triton to utilize the GPUs.*
```bash
curl -o nvidia-daemonset.yaml https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded-latest.yaml
kubectl apply -f nvidia-daemonset.yaml
```

**5. Deploy Applications:**
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

## 6. Troubleshooting

### Debugging Stuck Node Provisioning
If `terraform apply` hangs while creating node pools (often caused by GPU stockouts or quota limits), follow these steps to force a fix:

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
Look for a `statusMessage` detailing why it failed (e.g. "Insufficient regional quota"):
```bash
gcloud container node-pools describe triton-machine-learning-node-pool --cluster machine-learning-cluster --location europe-west1-b
```

**4. Delete the stuck node pool manually to unblock Terraform:**
```bash
gcloud container node-pools delete triton-machine-learning-node-pool --cluster machine-learning-cluster --zone europe-west1-b --quiet
```
*(Note: If GCP says "Cluster is running incompatible operation", you must wait for GCP's internal 35-minute timeout to finish before you can delete the pool).*

---

## 7. Next Steps & Roadmap

- [x] Verified Git Autonomy.
- **Move the Terraform state file** to a Google Cloud Storage backend for shared state management.
- Ensure environment variables identifying each machine/pod are injected properly.
- Finalize Secrets Manager integration.
- Ensure seamless VPC communication between all components.

---
*Note: This infrastructure setup is highly autonomous. Terraform may destroy and recreate resources (like Node Pools) automatically to bypass cloud capacity limits.*