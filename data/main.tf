terraform {
  required_version = ">= 1.6"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

variable "app_name"    { default = "localcloud" }
variable "app_version" { default = "1.0.0"      }
variable "db_password" { sensitive = true        }

locals {
  labels = {
    app     = var.app_name
    version = var.app_version
    managed = "terraform"
  }
}

resource "docker_network" "app" {
  name = "${var.app_name}-net"
}

resource "docker_volume" "postgres" {
  name = "${var.app_name}-postgres"
}

resource "docker_volume" "minio" {
  name = "${var.app_name}-minio"
}

resource "docker_container" "postgres" {
  name  = "${var.app_name}-postgres"
  image = "postgres:16-alpine"

  env = [
    "POSTGRES_DB=localcloud",
    "POSTGRES_USER=localcloud",
    "POSTGRES_PASSWORD=${var.db_password}",
  ]

  volumes {
    volume_name    = docker_volume.postgres.name
    container_path = "/var/lib/postgresql/data"
  }

  networks_advanced { name = docker_network.app.name }
  labels { label = "app" value = var.app_name }
}

resource "docker_container" "minio" {
  name  = "${var.app_name}-minio"
  image = "minio/minio:latest"

  command = ["server", "/data", "--console-address", ":9001"]

  volumes {
    volume_name    = docker_volume.minio.name
    container_path = "/data"
  }

  ports {
    internal = 9000
    external = 9000
  }

  networks_advanced { name = docker_network.app.name }
}

output "postgres_host" {
  value = docker_container.postgres.name
}
