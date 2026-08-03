# 0. Enable Required Google Cloud APIs
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "compute.googleapis.com",             # For VPC, Subnets, NAT, and VMs
    "container.googleapis.com",           # For Kubernetes Engine
    "artifactregistry.googleapis.com",    # For the Docker repository
    "bigquery.googleapis.com",            # For the prediction history dataset/table
    "iam.googleapis.com",                 # For creating the custom Service Account
    "cloudresourcemanager.googleapis.com" # For assigning IAM roles to the Service Account
  ])

  project = "ml-ops-classifier-app"
  service = each.key

  # We set this to false so that running 'terraform destroy' does not accidentally
  # disable the APIs before it finishes deleting the infrastructure that relies on them.
  disable_on_destroy = false
}
# 1. Definition of the Virtual Private Cloud Network
resource "google_compute_network" "machine_learning_virtual_private_network" {
  name                    = "machine-learning-virtual-private-network"
  auto_create_subnetworks = false

  # Wait for the APIs to be enabled before creating the network
  depends_on = [google_project_service.enabled_apis]
}

# 2. Define a Subnetwork for the Kubernetes Cluster
resource "google_compute_subnetwork" "kubernetes_sub_network" {
  name          = "kubernetes-sub-network"
  ip_cidr_range = "10.0.0.0/16"
  region        = "europe-west3"
  network       = google_compute_network.machine_learning_virtual_private_network.id
}

# 3. Define the Google Kubernetes Engine (GKE) Cluster (Control Plane only)
#    - Zonal cluster to save costs for learning
resource "google_container_cluster" "primary_cluster" {
  name     = "machine-learning-cluster"
  location = "europe-west3-a"

  # Attach it to the VPC and Subnet created above
  network    = google_compute_network.machine_learning_virtual_private_network.id
  subnetwork = google_compute_subnetwork.kubernetes_sub_network.id

  # We disable deletion protection so we can easily destroy and recreate our learning cluster when needed.
  deletion_protection = false

  # Delete the default node pool created by GCP so we can define a dedicated node pool later
  remove_default_node_pool = true

  # Required by the Google API: even though we delete the default pool immediately,
  # the API requires setting an initial count of at least 1 node during creation.
  initial_node_count = 1

  # Turning this empty block on enables VPC-Native routing (Alias IPs).
  # This ensures every Kubernetes Pod gets its own real, routable IP address from our subnet.
  ip_allocation_policy {}

  private_cluster_config {
    # Hides worker VMs from the internet. They receive ONLY private internal IP addresses.
    enable_private_nodes = true

    # Controls access to the Kubernetes API server (Control Plane / Master).
    # Setting to 'false' assigns a public IP to the API server so we can run 'kubectl' from our local Machines.
    enable_private_endpoint = false

    # Reserved private IP range (/28 = 16 IPs) for Google to host the managed Control Plane.
    # Must NOT overlap with our VPC network range (10.0.0.0/16).
    # [/28 meaning 28 bits locked so 2^4 available ip's]
    master_ipv4_cidr_block = "172.16.0.0/28"
  }

}


# 4. Create a Custom Service Account for the GKE Nodes
resource "google_service_account" "kubernetes_node_service_account" {
  account_id   = "ml-node-service-account"
  display_name = "Custom Service Account for GKE Nodes"
}

# 5. Assign IAM Roles to the Custom Service Account
# We use google_project_iam_member to grant specific permissions to our service account.
# Allows our nodes to send system and application logs to Cloud Logging
resource "google_project_iam_member" "node_service_account_logging" {
  project = "ml-ops-classifier-app"
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.kubernetes_node_service_account.email}"
}

# Allows our nodes to send metrics to Cloud Monitoring (Grafana/Prometheus)
resource "google_project_iam_member" "node_service_account_monitoring" {
  project = "ml-ops-classifier-app"
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.kubernetes_node_service_account.email}"
}

# Allows our nodes to pull Docker images from Artifact Registry / Container Registry
resource "google_project_iam_member" "node_service_account_registry" {
  project = "ml-ops-classifier-app"
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.kubernetes_node_service_account.email}"
}

# Allows our nodes to read and write files (like user images) to Cloud Storage buckets
resource "google_project_iam_member" "node_service_account_storage" {
  project = "ml-ops-classifier-app"
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.kubernetes_node_service_account.email}"
}

# Allows our nodes to read and write prediction data to BigQuery tables
resource "google_project_iam_member" "node_service_account_bigquery" {
  project = "ml-ops-classifier-app"
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.kubernetes_node_service_account.email}"
}

# 6.a. Define the Custom Node Pool (The Worker Virtual Machines)
# First we start with nodes that only have CPUs
resource "google_container_node_pool" "gradio_nodes" {
  name       = "gradio-machine-learning-node-pool"
  location   = "europe-west3-a"
  cluster    = google_container_cluster.primary_cluster.name
  node_count = 2

  # Wait for the NAT gateway to be fully created before booting these nodes.
  # If they boot before the NAT, they can't download Kubernetes binaries from the internet and will get stuck provisioning.
  depends_on = [google_compute_router_nat.nat_gateway]

  # Define the machine types and set the gpu's
  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 50


    # Attach our custom Service Account to the nodes
    service_account = google_service_account.kubernetes_node_service_account.email

    # Using the single "cloud-platform" master scope, we instead rely entirely on the
    # fine-grained IAM roles we explicitly granted to the Service Account above.
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Free-text 'hashtags' stamped onto our VMs so our firewall rules can target them specifically later.
    tags = ["google-kubernetes-engine-node", "machine-learning-ops-cluster", "gradio-node"]
  }
}

resource "google_compute_reservation" "l4_reservation" {
  name = "l4-gpu-reservation"
  zone = "europe-west3-a"
  specific_reservation_required = true

  specific_reservation {
    count = 1
    instance_properties {
      machine_type = "g2-standard-4"
      guest_accelerators {
        accelerator_type  = "nvidia-l4"
        accelerator_count = 1
      }
    }
  }
}
# 6.b. Then the nodes that will a gpu since they must have a gpu
resource "google_container_node_pool" "triton_nodes" {
  name       = "triton-reserved-node-pool"
  location   = "europe-west3-a"
  cluster    = google_container_cluster.primary_cluster.name
  node_count = 1

  # Ensure the NAT is ready so this GPU node can reach the internet to download NVIDIA drivers on boot.
  # This prevents the node pool from getting tainted due to a race condition.
  depends_on = [google_compute_router_nat.nat_gateway]

  # Define the machine types and set the gpu's
  node_config {
    machine_type = "g2-standard-4"
    disk_size_gb = 50

    # Add GPU to the node
    guest_accelerator {
      type  = "nvidia-l4"
      count = 1
    }

    # Attach our custom Service Account to the nodes
    service_account = google_service_account.kubernetes_node_service_account.email

    # Using the single "cloud-platform" master scope, we instead rely entirely on the
    # fine-grained IAM roles we explicitly granted to the Service Account above.
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Free-text 'hashtags' stamped onto our VMs so our firewall rules can target them specifically later.
    tags = ["google-kubernetes-engine-node", "machine-learning-ops-cluster", "triton-node"]

    reservation_affinity {
      consume_reservation_type = "SPECIFIC_RESERVATION"
      key                      = "compute.googleapis.com/reservation-name"
      values                   = [google_compute_reservation.l4_reservation.name]
    }
  }
}

# 7. Create a Google Cloud Storage Bucket for User Images
resource "google_storage_bucket" "image_storage_bucket" {
  # WARNING: Cloud Storage bucket names must be GLOBALLY unique across all of Google Cloud.
  # You might need to add some random numbers to the end of this name so it doesn't clash.
  name     = "machine-learning-ops-images-bucket-2026"
  location = "europe-west1"

  # Setting this to true means if we ever want to destroy our project,
  # Terraform is allowed to delete this bucket even if there are images inside it.
  force_destroy = true

  uniform_bucket_level_access = true
}

# 8. Create a BigQuery Dataset (The container for our tables)
resource "google_bigquery_dataset" "prediction_dataset" {
  dataset_id = "machine_learning_predictions_euw3"
  location   = "europe-west3"

  # Equivalent to force_destroy. Allows Terraform to delete this dataset
  # even if it still contains tables.
  delete_contents_on_destroy = true
}

# 9. Create the BigQuery Table and define its columns
resource "google_bigquery_table" "prediction_history_table" {
  dataset_id = google_bigquery_dataset.prediction_dataset.dataset_id
  table_id   = "inference_history"

  # Terraform defaults this to true for BigQuery tables as a safety measure.
  # We set it to false so we can successfully run 'terraform destroy' later.
  deletion_protection = false

  schema = <<EOF
    [
      {"name": "uuid", "type": "STRING", "mode": "REQUIRED"},
      {"name": "predicted_class", "type": "STRING", "mode": "NULLABLE"},
      {"name": "probability", "type": "FLOAT", "mode": "NULLABLE"},
      {"name": "timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
      {"name": "kubernetes_node", "type": "STRING", "mode": "NULLABLE"},
      {"name": "gcs_image_uri", "type": "STRING", "mode": "NULLABLE"},
      {"name": "additional_comment", "type": "STRING", "mode": "NULLABLE"}
    ]
    EOF
}

# 10. Create an Artifact Registry Repository for Docker Images
resource "google_artifact_registry_repository" "docker_repository" {
  location      = "europe-west3"
  repository_id = "machine-learning-artifacts-registry"
  description   = "Docker repository for Gradio and Triton container images"
  format        = "DOCKER"
}

# 11. Create a Cloud Router (Required by Cloud Network Address Translation [NAT])
resource "google_compute_router" "network_address_translation_router" {
  name    = "machine-learning-network-address-translation-router"
  region  = "europe-west3"
  network = google_compute_network.machine_learning_virtual_private_network.id
}

# 12. Create a Cloud NAT Gateway (Allows private VMs to access the internet)
# One vm tries to download an element X, it's request first goes to the NAT's gateway, the gateway takes that request
# strips it's information, appends it's own public IP, sends the request outside for the element X, when the element X
# is returned to the gateway, the gateway looks for which VM asked for X and send it to that specific VM.
resource "google_compute_router_nat" "nat_gateway" {
  name                               = "machine-learning-network-address-translation-gateway"
  router                             = google_compute_router.network_address_translation_router.name
  region                             = "europe-west3"
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}