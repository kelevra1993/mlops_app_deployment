
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