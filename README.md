
Gcloud Steps : 
- Revoke everything before starting
  - gcloud auth revoke --all
- Connect to gcloud via cli
  - gcloud auth login
- If a project is set and you want to remove it
  - gcloud config unset project
- Set up application default credentials
  - gcloud auth application-default login


Terraform Steps On Mac:
- Install Hashicorp Tap :
  - brew tap hashicorp/tap
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
  - terraform apply : For applying changes

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

- Configure connection to Artifact Registry
  - gcloud auth configure-docker "LOCATION"-docker.pkg.dev
In our case : "gcloud auth configure-docker europe-west4-docker.pkg.dev"

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