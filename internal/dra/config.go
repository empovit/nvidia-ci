package dra

import (
	"strings"

	"github.com/golang/glog"
	"github.com/kelseyhightower/envconfig"
)

// DRAConfig holds DRA installation configuration loaded from environment variables
// and programmatically set Helm chart values.
type DRAConfig struct {
	chartSource   string
	chartVersion  string
	imageRegistry string
	imageTag      string

	// Values holds Helm chart values that can be set programmatically.
	// These values are merged with environment-based configuration.
	Values map[string]interface{}
}

// LoadConfig loads DRA configuration from environment variables.
// Environment variables are loaded into both struct fields and the Values map.
// If environment variables are not set, uses the defaults specified in struct tags.
//
// Environment Variable Examples:
//   DRA_CHART_SOURCE:
//     - "https://helm.ngc.nvidia.com/nvidia" (default - Helm repository)
//     - "https://custom-repo.com/charts" (custom Helm repository)
//     - "oci://ghcr.io/nvidia/k8s-dra-driver-gpu" (OCI registry)
//     - "/path/to/chart" or "file:///path/to/chart" (local filesystem)
//   DRA_CHART_VERSION:
//     - "latest" (default)
//     - "25.12.0-dev-39e21b3c-chart" (specific version)
//   DRA_IMAGE_REGISTRY:
//     - "" (default - use chart's default)
//     - "nvcr.io/nvidia/cloud-native" (override image registry)
//   DRA_IMAGE_TAG:
//     - "" (default - use chart's default)
//     - "v1.2.3" (override image tag)
func LoadConfig() (*DRAConfig, error) {
	// Temporary struct for envconfig (requires exported fields)
	temp := struct {
		ChartSource   string `envconfig:"DRA_CHART_SOURCE" default:"https://helm.ngc.nvidia.com/nvidia"`
		ChartVersion  string `envconfig:"DRA_CHART_VERSION" default:"latest"`
		ImageRegistry string `envconfig:"DRA_IMAGE_REGISTRY" default:""`
		ImageTag      string `envconfig:"DRA_IMAGE_TAG" default:""`
	}{}

	err := envconfig.Process("", &temp)
	if err != nil {
		return nil, err
	}

	// Create DRAConfig with values from environment variables
	config := &DRAConfig{
		chartSource:   temp.ChartSource,
		chartVersion:  temp.ChartVersion,
		imageRegistry: temp.ImageRegistry,
		imageTag:      temp.ImageTag,
		Values:        make(map[string]interface{}),
	}

	// Populate Values map from environment variables
	if config.imageRegistry != "" {
		image := ensureMap(config.Values, "image")
		image["repository"] = config.imageRegistry
	}
	if config.imageTag != "" {
		image := ensureMap(config.Values, "image")
		image["tag"] = config.imageTag
	}

	return config, nil
}

// ensureMap ensures a key in the parent map contains a map[string]interface{}.
// If the key is nil, creates a new map. If the key exists but is not a map, panics.
//
// IMPORTANT: The panic on type mismatch is INTENTIONAL. This function validates internal
// invariants in the DRAConfig builder pattern. A type mismatch indicates a programming bug
// (incorrect builder usage or logic error), not a runtime condition that should be handled
// gracefully. Failing fast with glog.Fatalf makes debugging easier by catching bugs immediately
// rather than propagating corrupt state. DO NOT change this to return an error.
func ensureMap(parent map[string]interface{}, key string) map[string]interface{} {
	if parent[key] == nil {
		m := make(map[string]interface{})
		parent[key] = m
		return m
	}
	m, ok := parent[key].(map[string]interface{})
	if !ok {
		glog.Fatalf("%s field is not a map[string]interface{}", key)
	}
	return m
}

// WithGPUResources sets the resources.gpus.enabled value.
func (c *DRAConfig) WithGPUResources(enabled bool) *DRAConfig {
	resources := ensureMap(c.Values, "resources")
	gpus := ensureMap(resources, "gpus")
	gpus["enabled"] = enabled
	return c
}

// WithGPUResourcesOverride sets the gpuResourcesEnabledOverride value.
func (c *DRAConfig) WithGPUResourcesOverride(override bool) *DRAConfig {
	c.Values["gpuResourcesEnabledOverride"] = override
	return c
}

// WithImageRegistry sets the image repository in the Values map.
func (c *DRAConfig) WithImageRegistry(registry string) *DRAConfig {
	image := ensureMap(c.Values, "image")
	image["repository"] = registry
	return c
}

// WithImageTag sets the image tag in the Values map.
func (c *DRAConfig) WithImageTag(tag string) *DRAConfig {
	image := ensureMap(c.Values, "image")
	image["tag"] = tag
	return c
}

// WithChartSource sets the chart source location.
func (c *DRAConfig) WithChartSource(source string) *DRAConfig {
	c.chartSource = source
	return c
}

// WithChartVersion sets the chart version.
func (c *DRAConfig) WithChartVersion(version string) *DRAConfig {
	c.chartVersion = version
	return c
}

// IsOCI returns true if ChartSource points to an OCI registry (starts with "oci://").
func (c *DRAConfig) IsOCI() bool {
	return strings.HasPrefix(c.chartSource, "oci://")
}

// IsLocal returns true if ChartSource points to a local filesystem path.
// Recognizes paths starting with "file://" or absolute paths starting with "/".
func (c *DRAConfig) IsLocal() bool {
	return strings.HasPrefix(c.chartSource, "file://") || strings.HasPrefix(c.chartSource, "/")
}

// IsRepo returns true if ChartSource is a Helm repository.
// Recognizes URLs starting with "http://" or "https://" as Helm repository URLs.
func (c *DRAConfig) IsRepo() bool {
	return strings.HasPrefix(c.chartSource, "http://") || strings.HasPrefix(c.chartSource, "https://")
}

// GetOCIRef returns the OCI reference for OCI-based installations.
func (c *DRAConfig) GetOCIRef() string {
	return c.chartSource
}

// GetLocalPath returns the local filesystem path for local installations.
// Strips "file://" prefix if present.
func (c *DRAConfig) GetLocalPath() string {
	return strings.TrimPrefix(c.chartSource, "file://")
}

// GetRepoURL returns the Helm repository URL.
// ChartSource should be an http:// or https:// URL.
func (c *DRAConfig) GetRepoURL() string {
	return c.chartSource
}

// GetChartVersion returns the chart version.
func (c *DRAConfig) GetChartVersion() string {
	return c.chartVersion
}

// GetChartSource returns the chart source (for logging/debugging).
func (c *DRAConfig) GetChartSource() string {
	return c.chartSource
}
