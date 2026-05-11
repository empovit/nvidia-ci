#!/usr/bin/env bash
#
# get-latest-dra-chart.sh - Fetch the latest DRA driver Helm chart tag from GCP Artifact Registry
#
# REQUIREMENTS:
#   - jq must be installed for JSON parsing
#   - curl must be installed for API requests
#
# USAGE:
#   ./scripts/get-latest-dra-chart.sh
#
# OUTPUT:
#   - stderr: Human-readable message with OCI chart URL and tag
#   - stdout: Just the tag (for easy variable capture)

set -euo pipefail

REGISTRY="us-central1-docker.pkg.dev"
REPO="k8s-staging-images/dra-driver-nvidia/charts"
CHART="dra-driver-nvidia-gpu"
API_URL="https://${REGISTRY}/v2/${REPO}/${CHART}/tags/list"
CHART_URL="oci://${REGISTRY}/${REPO}/${CHART}"

# Fetch tags from GCP Artifact Registry (no authentication needed for public repos)
response=$(curl --fail-with-body -sSL "${API_URL}")

# Get the most recent tag by timeUploadedMs
tag=$(echo "$response" | jq -r '.manifest | to_entries | sort_by(.value.timeUploadedMs | tonumber) | reverse | .[0].value.tag[0] // empty')

if [ -z "$tag" ] || [ "$tag" = "null" ]; then
    echo "Error: No Helm chart tags found in registry" >&2
    echo "$response" >&2
    exit 1
fi

# Output to stderr for human readability
echo "Found latest Helm chart: ${CHART_URL}:${tag}" >&2

# Output only the tag to stdout for easy variable assignment
echo "${tag}"
