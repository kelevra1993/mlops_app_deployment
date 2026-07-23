
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