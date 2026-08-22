terraform {
  backend "gcs" {
    # This is where we will store the terraform state file.
    # We chose to store it on google cloud for management of infrastructure from different devices
    bucket = "ml-ops-infrastructure-2026"
    prefix = "terraform/state"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.8.0"
    }
  }
}

provider "google" {
  project = "ml-ops-classifier-app"

  # These values are pulled from the variables defined at the top of main.tf
  # using the "var." namespace.
  region = var.region
  zone   = var.zone
}